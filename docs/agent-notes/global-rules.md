# Global Rules

## Project Structure

- `backend/`: FastAPI, SQLAlchemy, Alembic, pytest.
- `frontend/`: Vite, React, Firebase client auth.
- Root Alembic config lives at `alembic.ini`; run Alembic from the repo root.

## Development Mode

- Pickup Lane is still pre-production.
- If a data model needs to change and the user says the database can be wiped, update the existing feature migration/model/schema files instead of adding extra cleanup migrations.
- Add a new migration only when the user wants production-safe migration history or the branch has already shipped.
- Do not create unrelated tables, routes, features, or abstractions.
- Keep edits tightly scoped to the active request.

## Secrets And Local Files

- Never commit `.env`, `.env.*`, Firebase admin JSON/service account keys, or local virtualenv folders.
- `frontend/.env.local` and `backend/.env` are local secrets and must stay ignored.
- Firebase admin key files must stay ignored.
- Dev-only scripts that create Firebase test users should not be pushed unless the user explicitly changes that decision.

## Git And PR Hygiene

- Check `git status -sb` before staging.
- After checking status/diff, use `git add .` by default when the tree only
  contains intended tracked/untracked work.
- Do not list every file in `git add` unless partial staging is actually
  needed.
- Stage explicit paths only when the tree is mixed or unexpected files need to
  stay out of the commit.
- Do not stage ignored local secrets.
- `AGENTS.md` and unapproved local notes under `docs/agent-notes/` are local-only working notes and must stay ignored.
- The durable repository-visible standards under `docs/agent-notes/` are limited to `global-rules.md`, `app-testing-standards.md`, `backend-testing.md`, `backend-structure.md`, `database.md`, `frontend-structure.md`, and `playwright-structure.md`.
- Provide a concise PR description with summary and validation.
- If asked to push, verify no secret files are in `git status`.

## Working Style

- Prefer direct implementation once the user says to proceed.
- If the user says "don't code yet," discuss only.
- Prefer directness and best-practice pushback over agreement for its own sake.
- In tense discussions, stay calm and focus on the concrete fix.

## Commands And Verification

- Do not run migrations unless the user explicitly asks.
- Do not run backend API tests unless the user explicitly asks.
- Do not run broad test suites unless the user explicitly asks.
- Do not create redundant migration scripts during development cleanup.
- For backend changes, tell the user which focused API tests or commands they
  should run manually.
- Static checks, compilation, import checks, route-registration checks,
  structural searches, and `git diff --check` may be run when they do not
  mutate application or database state.
- Before backend implementation, confirm the files to be changed and the
  ownership of new or moved logic.
