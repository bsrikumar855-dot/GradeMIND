# Credential Rotation Checklist

**Status: NOT EXECUTED. This is a checklist for a human.**
**Phase:** 0 (Containment), item 1.8

No credential in this document has been rotated by tooling or by an agent, and
none should be. Rotation requires access to provider consoles and production
secret stores; it is deliberately outside what automation here touches.

---

## Why rotate

Treat every secret that has ever appeared in this repository, its history, its
CI configuration, or a developer's shell as compromised. Specifically:

- `docker-compose.yml` shipped `SECRET_KEY: change_me_in_production` as a
  literal, and commit `a6a1107` records a merge that silently **restored**
  hardcoded `POSTGRES_PASSWORD` and `SECRET_KEY` values after they had been
  removed — so the window is longer than a single commit's lifetime.
- `GROQ_API_KEY` reappeared in the same bad merge after Groq had been removed.
- The repository is shared across at least six collaborators and several
  deployment targets.

A secret that was ever in a shared repo is public until proven otherwise.
Rotating is cheap; assuming is not.

## Order matters

Rotate in this order so the application is never running with a key that no
longer opens the lock:

1. Provision the **new** secret alongside the old one where the provider
   supports dual-validity (databases, most API providers).
2. Update the secret store / environment.
3. Redeploy and confirm health.
4. **Then** revoke the old secret.
5. Confirm the old secret fails.

For `SECRET_KEY` specifically, step 4 invalidates every issued JWT. All users
are logged out. Schedule it accordingly, and tell people.

---

## Checklist

### `SECRET_KEY` (JWT signing)

- [ ] Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] Set in the production secret store (not `.env` in a repo, not compose literals)
- [ ] Set in staging
- [ ] Redeploy backend
- [ ] Confirm login works and old tokens are rejected
- [ ] **Blast radius:** every active session is invalidated. All users log out.

### `DATABASE_URL` / `POSTGRES_PASSWORD`

- [ ] Create a new DB role, or rotate the password on the existing one
- [ ] Update `DATABASE_URL` in the secret store
- [ ] Redeploy backend; confirm migrations and health check pass
- [ ] Revoke the old password
- [ ] Confirm the old credential is refused
- [ ] **Blast radius:** total outage if wrong. Do this in a maintenance window.

### `GEMINI_API_KEY`

- [ ] Revoke the existing key in Google AI Studio / Cloud console
- [ ] Issue a new key, restricted to the minimum required API surface
- [ ] Update the secret store
- [ ] Confirm the secondary evaluator still responds
- [ ] **Blast radius:** the Gemini cross-check evaluator fails. Per the master
      spec this must degrade the *lane* toward human review and never the
      *mark* — verify that is what actually happens before assuming it is safe.

### `GROQ_API_KEY`

- [ ] Revoke. Groq was removed in favour of Gemini; there should be no live
      consumer. Revoke rather than rotate.
- [ ] Confirm no code path still reads it:
      `grep -rn "GROQ" --include=*.py --include=*.yml .`

### Vercel tokens

- [ ] Revoke all personal and project deploy tokens in Vercel account settings
- [ ] Reissue scoped to the single project
- [ ] Update any GitHub Actions secret that holds one
- [ ] **Blast radius:** frontend deploys fail until updated.

### GitHub

- [ ] Audit repository secrets: Settings → Secrets and variables → Actions
- [ ] Remove any secret no longer used
- [ ] Audit deploy keys and PATs with write access to this repo
- [ ] If a fine-grained PAT is created for CI log reading (Phase 0 gate
      verification), scope it to `actions: read` on this repository only, keep
      it in the environment, and never in the tree

### Vercel deployment cleanup — tracked, not remembered

The project has **205 deployments** (owner-observed in the Vercel dashboard).
Vercel keeps every past deployment reachable at its own immutable
`grade-mind-<hash>.vercel.app` URL indefinitely unless deleted. Any deployment
built from a commit **before `1090c1f`** still contains
`frontend/src/app/api/run-cmd/route.ts`.

**Severity: hygiene, not emergency.** The route hardcodes
`cwd: 'd:\GradeMIND\frontend'`, which does not exist on a Linux host, so
`child_process.exec` raises ENOENT before running the command and the endpoint
returns a 500 rather than executing. Verified by reproduction — see
`docs/phases/PHASE_0_REPORT.md`. It is a working RCE only on a Windows host.

Leaving an unknown number of public URLs each carrying a shell-exec route is
still not a state to leave things in.

- [ ] Identify which of the 205 deployments predate `1090c1f`
- [ ] Delete those, keeping whatever is needed for the competition record
- [ ] Enable auto-delete for preview deployments so this does not re-accumulate
- [ ] Check function logs for requests to `/api/run-cmd`. A hit means someone
      probed; given the ENOENT behaviour it does **not** mean they got
      anything. Evidence of attempted access, not of exfiltration.
- [ ] Confirm the project's production branch is `main` (it builds the default
      branch unless configured otherwise)

### Developer machines

- [ ] Every collaborator deletes stale `.env` files containing old secrets
- [ ] Every collaborator clears local logs that may contain them —
      see `docs/RUNBOOK_LOCAL_DEV.md` and `docs/HISTORY_REWRITE.md` §6

---

## After rotation

- [ ] Confirm `.env` is gitignored and only `.env.example` is committed
      (the pre-commit hook enforces this)
- [ ] Confirm `docker-compose.yml` contains no secret literals — only
      `${VAR:?message}` references
- [ ] Record the rotation date here:

| Secret | Rotated on | By |
|---|---|---|
| `SECRET_KEY` | | |
| `DATABASE_URL` | | |
| `GEMINI_API_KEY` | | |
| `GROQ_API_KEY` (revoked) | | |
| Vercel tokens | | |
