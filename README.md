# pickup-lane

## Prototype Deployment

This repo is currently deployed as a portfolio prototype with fake/demo data.
Keep Stripe in test mode and never commit local `.env` files, Firebase service
account JSON, or provider secrets.

Recommended free-tier services:

- Frontend: Vercel
- Backend API: Render Web Service
- Database: Neon Postgres
- Auth: Firebase Auth
- Media storage: Cloudflare R2
- Payments: Stripe test mode

Backend deploy settings for Render:

```bash
pip install -r backend/requirements.txt
```

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Important backend environment variables:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
INBOX_TOKEN_SECRET=...
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
ENABLE_API_DOCS=false
ENABLE_DB_HEALTH=false
FIREBASE_ADMIN_CREDENTIALS_JSON={...}
ENABLE_STRIPE_PAYMENTS=false
STRIPE_SECRET_KEY=...
STRIPE_PUBLISHABLE_KEY=...
STRIPE_WEBHOOK_SECRET=...
STRIPE_CURRENCY=USD
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
R2_ENDPOINT_URL=...
```

Backend `APP_ENV` must be one of `local`, `test`, `ci`, `preview`, `staging`,
or `production`. If `APP_ENV` is unset outside CI and no deployed-runtime marker
is present, the backend defaults to `local`. Local development may use ignored
`backend/.env`; deployed preview, staging, and production environments must
inject settings directly. Production must keep public API docs disabled and must
use an independent `INBOX_TOKEN_SECRET`, not `DATABASE_URL` or another provider
credential.

Frontend deploy settings for Vercel:

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`

Important frontend environment variables:

```text
VITE_API_BASE_URL=https://your-render-service.onrender.com
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

`frontend/vercel.json` rewrites all routes to `index.html` so React Router
deep links work on Vercel.

## Production Readiness Governance

Production-readiness artifacts live in `docs/production-readiness/00-READ-ME-FIRST.md`.
WS01 governance artifacts live in `docs/production-readiness/governance/README.md`.
