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
DATABASE_URL=postgresql+psycopg://...
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
FIREBASE_ADMIN_CREDENTIALS_JSON={...}
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
R2_ENDPOINT_URL=...
```

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
