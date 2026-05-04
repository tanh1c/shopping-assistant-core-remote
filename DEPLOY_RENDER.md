# Deploying on Render

This repo is prepared for a 3-service Render deployment:

- `shopping-assistant-frontend`: Static Site
- `shopping-assistant-backend`: Docker Web Service
- `shopping-assistant-ai-pipeline`: Docker Web Service

The current [render.yaml](./render.yaml) is tuned for the Render free tier.

## Files

- Blueprint: [render.yaml](./render.yaml)
- Render backend image: [backend/Dockerfile.render](./backend/Dockerfile.render)
- Render AI pipeline image: [ai-pipeline/Dockerfile.render](./ai-pipeline/Dockerfile.render)

## Recommended setup

1. Push the repo to GitHub.
2. In Render, choose `New` -> `Blueprint`.
3. Point Render to this repo and use `render.yaml`.
4. During creation, provide `OPENAI_API_KEY` for `shopping-assistant-ai-pipeline`.

## Important notes

- The backend keeps a local replica file at `/tmp/shopping.db`.
- For durable free storage, set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` on the backend service.
- Without Turso, `/tmp/shopping.db` is ephemeral and can be lost whenever the free service restarts or spins down.
- The reference-price CSV is baked into the backend image at `/app/data/reference_prices.csv`.
- The AI pipeline syncs to the backend over the backend's public Render URL.
- The AI pipeline must stay a public web service so Raspberry Pi can call `POST /infer`.
- Free web services spin down after idle time, so the first request after idle can be slow.

## Recommended free database setup

Use Turso for the backend database while keeping the backend web service on Render Free.

Backend env vars:

```text
TURSO_DATABASE_URL=libsql://<your-db>-<your-org>.turso.io
TURSO_AUTH_TOKEN=<your-token>
SHOPPING_DB_PATH=/tmp/shopping.db
TURSO_SYNC_INTERVAL_SECONDS=30
```

## Frontend API URL

The blueprint sets:

```text
VITE_API_BASE_URL=https://shopping-assistant-backend.onrender.com
```

If Render gives the backend a different public hostname, update the frontend service env var:

```text
VITE_API_BASE_URL=https://<your-actual-backend-host>.onrender.com
```

Then redeploy the frontend.

## After deploy

- Frontend should open publicly on its Render URL.
- Backend docs should be available at `/api/docs`.
- AI pipeline health should be available at `/health`.
- Raspberry Pi should send images to the AI pipeline public URL, not the backend URL.
