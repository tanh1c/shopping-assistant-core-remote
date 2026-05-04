# Deploying on Render

This repo is prepared for a 3-service Render deployment:

- `shopping-assistant-frontend`: Static Site
- `shopping-assistant-backend`: Docker Web Service
- `shopping-assistant-ai-pipeline`: Docker Web Service

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

- The backend uses a persistent disk mounted at `/var/data`.
- The backend stores SQLite at `/var/data/shopping.db`.
- The reference-price CSV is baked into the backend image at `/app/data/reference_prices.csv`.
- The AI pipeline syncs to the backend over Render private networking via `BACKEND_HOSTPORT`.
- The AI pipeline must stay a public web service so Raspberry Pi can call `POST /infer`.

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
