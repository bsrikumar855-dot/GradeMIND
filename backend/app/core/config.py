import os
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Environment(str, Enum):
    """Where this process is running.

    Not a free-form string: an unrecognised value must fail loudly rather than
    silently falling outside the `local` branch and being treated as
    production-ish, or worse, matching a typo'd check somewhere.
    """

    LOCAL = "local"
    CI = "ci"
    STAGING = "staging"
    PRODUCTION = "production"


class AuthBypassNotPermitted(RuntimeError):
    """AUTH_ENABLED=False was requested outside local development.

    Raised at Settings construction — that is, at import time — so a
    misconfigured deployment cannot start and serve a single unauthenticated
    request. Failing at request time would mean the process comes up healthy,
    passes its health check, and serves every caller as an anonymous ADMIN.
    """


class Settings(BaseSettings):
    PROJECT_NAME: str = "GradeMIND Backend"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # default to 60 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEBUG: bool = False

    # Defaults to the most restrictive value. An unset ENVIRONMENT must not be
    # the one that permits the auth bypass.
    ENVIRONMENT: Environment = Environment.PRODUCTION

    # Secure by default. Disabling auth requires ALL THREE of
    # AUTH_ENABLED=False, DEBUG=True, ENVIRONMENT=local, simultaneously —
    # see _reject_auth_bypass_outside_local below.
    AUTH_ENABLED: bool = True
    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001"
    )
    # Deliberately no origin *regex*. The previous value was
    # r"https://.*\.vercel\.app", which combined with allow_credentials=True
    # matched any third party's Vercel deployment and let it make credentialed
    # cross-origin calls against this API. Preview deployments must be listed
    # explicitly in CORS_ALLOWED_ORIGINS like any other origin.
    # See docs/audit/BASELINE_AUDIT.md D11.

    # Gemini API Configuration (optional secondary/cross-check evaluator;
    # core grading works with zero LLM keys via the local autonomous evaluator)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_env(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes", "on"}:
                return True
        return value

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def parse_environment(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def _reject_auth_bypass_outside_local(self) -> "Settings":
        """The auth bypass requires all three flags, or the process will not start.

        Exactly one combination is accepted:

            AUTH_ENABLED=False  AND  DEBUG=True  AND  ENVIRONMENT=local

        Every other combination in which AUTH_ENABLED is False raises. When
        AUTH_ENABLED is True the other two flags are unconstrained — they carry
        no authorization meaning on their own.

        This is a triple gate rather than a single flag because AUTH_ENABLED
        alone has already been flipped by accident once: the merge fixed in
        a6a1107 appended a duplicate `AUTH_ENABLED: "False"` to
        docker-compose.yml, and YAML silently keeps the last occurrence. A
        single misplaced line reverted the whole authorization model with no
        conflict marker and no failing test. Requiring DEBUG and ENVIRONMENT to
        agree means an accident has to happen three times, in three places, and
        still land on the one host class where it is survivable.
        """
        if self.AUTH_ENABLED:
            return self

        conditions = {
            "DEBUG=True": self.DEBUG,
            'ENVIRONMENT="local"': self.ENVIRONMENT == Environment.LOCAL,
        }
        unmet = [name for name, ok in conditions.items() if not ok]

        if unmet:
            raise AuthBypassNotPermitted(
                "AUTH_ENABLED=False is only permitted for local development, "
                "and requires DEBUG=True and ENVIRONMENT=local at the same "
                f"time. Unmet: {', '.join(unmet)}. "
                f"(ENVIRONMENT={self.ENVIRONMENT.value}, DEBUG={self.DEBUG}). "
                "With auth disabled every request is served as an anonymous "
                "ADMIN, so this must never be reachable outside a developer's "
                "own machine."
            )

        return self

    # Configure Pydantic settings to load from .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instantiate the singleton settings object
settings = Settings()


def get_cors_allowed_origins() -> list[str]:
    return [
        origin.strip().rstrip("/")
        for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
