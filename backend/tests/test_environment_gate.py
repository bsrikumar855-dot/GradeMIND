"""Exhaustive matrix over the auth-bypass triple gate.

Audit item 0.6. `AUTH_ENABLED` defaulting to True was the D2 fix; this is the
rest of it — disabling auth must require `AUTH_ENABLED=False` **and**
`DEBUG=True` **and** `ENVIRONMENT=local` at the same time, and must fail at
`Settings` construction (import time) rather than at request time.

Import time matters: a process that starts, passes its health check, and only
then serves every caller as an anonymous ADMIN is worse than one that refuses
to boot.

The gate is a triple rather than a single flag because `AUTH_ENABLED` has been
flipped by accident before — commit a6a1107 fixed a merge that appended a
duplicate `AUTH_ENABLED: "False"` to docker-compose.yml, which YAML resolves by
keeping the last occurrence.
"""

import itertools

import pytest

from app.core.config import AuthBypassNotPermitted, Environment, Settings

REQUIRED = {"DATABASE_URL": "sqlite:///./test.db", "SECRET_KEY": "test-secret"}

# The one and only accepted bypass combination.
PERMITTED = (False, True, Environment.LOCAL)

# Variables that would otherwise leak in from the shell or CI job.
_AMBIENT = ("ENVIRONMENT", "AUTH_ENABLED", "DEBUG")


@pytest.fixture(autouse=True)
def isolate_from_ambient_env(monkeypatch):
    """Clear the gate's inputs from the process environment.

    `_env_file=None` stops pydantic-settings reading backend/.env, but OS
    environment variables still win over defaults. Without this, a test
    asserting the *default* value of ENVIRONMENT passes or fails depending on
    what the developer happened to export — which is precisely the class of
    environment-dependent behaviour this module exists to pin down.
    """
    for name in _AMBIENT:
        monkeypatch.delenv(name, raising=False)


def _build(auth_enabled: bool, debug: bool, environment: Environment) -> Settings:
    return Settings(
        AUTH_ENABLED=auth_enabled,
        DEBUG=debug,
        ENVIRONMENT=environment,
        _env_file=None,
        **REQUIRED,
    )


def _combinations():
    return itertools.product([True, False], [True, False], list(Environment))


def _is_permitted(auth_enabled: bool, debug: bool, environment: Environment) -> bool:
    # AUTH_ENABLED=True is always fine; the other two carry no authorization
    # meaning on their own.
    if auth_enabled:
        return True
    return (auth_enabled, debug, environment) == PERMITTED


@pytest.mark.parametrize("auth_enabled,debug,environment", list(_combinations()))
def test_full_matrix(auth_enabled, debug, environment):
    """All 16 combinations. Exactly the permitted ones construct."""
    if _is_permitted(auth_enabled, debug, environment):
        settings = _build(auth_enabled, debug, environment)
        assert settings.AUTH_ENABLED is auth_enabled
        assert settings.ENVIRONMENT is environment
    else:
        with pytest.raises(AuthBypassNotPermitted):
            _build(auth_enabled, debug, environment)


def test_exactly_one_bypass_combination_exists():
    """Counted, not assumed.

    Guards against a future edit that loosens the condition — e.g. swapping an
    `and` for an `or` — which the parametrized test above would still pass in
    aggregate if someone also updated _is_permitted to match.
    """
    accepted = []
    for auth_enabled, debug, environment in _combinations():
        try:
            _build(auth_enabled, debug, environment)
        except AuthBypassNotPermitted:
            continue
        accepted.append((auth_enabled, debug, environment))

    bypass = [combo for combo in accepted if combo[0] is False]
    assert bypass == [PERMITTED], f"expected exactly one bypass combination, got {bypass}"


@pytest.mark.parametrize(
    "environment", [Environment.CI, Environment.STAGING, Environment.PRODUCTION]
)
def test_bypass_rejected_in_every_non_local_environment(environment):
    with pytest.raises(AuthBypassNotPermitted):
        _build(False, True, environment)


def test_bypass_rejected_locally_without_debug():
    """ENVIRONMENT=local is not sufficient on its own."""
    with pytest.raises(AuthBypassNotPermitted):
        _build(False, False, Environment.LOCAL)


def test_environment_defaults_to_production():
    """An unset ENVIRONMENT must not be the value that permits the bypass."""
    settings = Settings(_env_file=None, **REQUIRED)
    assert settings.ENVIRONMENT is Environment.PRODUCTION

    with pytest.raises(AuthBypassNotPermitted):
        Settings(AUTH_ENABLED=False, DEBUG=True, _env_file=None, **REQUIRED)


def test_unknown_environment_is_rejected():
    """Not a free-form string: a typo must fail, not fall through to non-local."""
    with pytest.raises(Exception) as exc_info:
        Settings(ENVIRONMENT="prodution", _env_file=None, **REQUIRED)
    assert not isinstance(exc_info.value, AuthBypassNotPermitted)


@pytest.mark.parametrize("raw,expected", [("LOCAL", Environment.LOCAL), (" local ", Environment.LOCAL), ("Production", Environment.PRODUCTION)])
def test_environment_parsing_is_case_and_space_insensitive(raw, expected):
    assert Settings(ENVIRONMENT=raw, _env_file=None, **REQUIRED).ENVIRONMENT is expected


@pytest.mark.parametrize(
    "environment", [Environment.CI, Environment.STAGING, Environment.PRODUCTION]
)
def test_local_dev_user_unreachable_outside_local(monkeypatch, environment):
    """Defence in depth: the anonymous ADMIN must refuse to exist elsewhere.

    Settings already blocks the combination that reaches this function, so this
    covers the case where that gate is bypassed — a mutated settings object, a
    reload, a refactor that builds Settings by another path.

    The identity is a per-process UUID. An audit row attributing a mark to it
    is unattributable once the process exits.
    """
    from app.api import auth_deps

    monkeypatch.setattr(auth_deps.settings, "ENVIRONMENT", environment, raising=False)

    with pytest.raises(RuntimeError, match="must never author an audit record"):
        auth_deps.get_local_dev_user()


def test_local_dev_user_allowed_in_local(monkeypatch):
    from app.api import auth_deps

    monkeypatch.setattr(
        auth_deps.settings, "ENVIRONMENT", Environment.LOCAL, raising=False
    )

    user = auth_deps.get_local_dev_user()
    assert user["role"] == "ADMIN"
    assert user["auth_disabled"] is True


def test_ci_is_not_an_accepted_bypass_environment():
    """Named explicitly, not just covered by the matrix.

    If someone later sets AUTH_ENABLED=False in CI to make a test pass, the
    gate must refuse rather than let the suite run without authorization.
    """
    with pytest.raises(AuthBypassNotPermitted):
        _build(False, True, Environment.CI)

    # And the combination CI actually runs with must construct fine.
    settings = _build(True, False, Environment.CI)
    assert settings.AUTH_ENABLED is True
    assert settings.ENVIRONMENT is Environment.CI


def test_error_names_which_conditions_were_unmet():
    """The message has to be actionable — this fires during a deploy."""
    with pytest.raises(AuthBypassNotPermitted) as exc_info:
        _build(False, False, Environment.PRODUCTION)

    message = str(exc_info.value)
    assert "DEBUG=True" in message
    assert 'ENVIRONMENT="local"' in message
