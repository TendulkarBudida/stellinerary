# Stellinerary Frontend

React and Vite client for the Stellinerary night-sky expedition planner.

## Local development

```bash
npm install
npm run dev
```

The client uses `http://localhost:8000` by default. Copy `.env.example` to
`.env.local` and set the backend URL when it is hosted elsewhere:

```bash
copy .env.example .env.local
```

Required frontend variable:

```text
VITE_API_BASE_URL=https://your-backend.example.com
```

## Verification without real APIs

```bash
npm test
npm run build
npm run lint
```

The Vitest suite mocks Axios and does not contact the backend.

## Deploy to Vercel

Create a Vercel project with `frontend` as the root directory. Set
`VITE_API_BASE_URL` to the deployed backend URL in the Vercel project
environment variables, then deploy.
