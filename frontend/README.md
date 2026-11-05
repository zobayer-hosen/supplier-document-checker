# Frontend (Next.js)

See the main [README](../README.md) for setup. Quick start:

```powershell
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000. The backend must be running on http://localhost:8000.

| Folder | What it holds |
|---|---|
| `app/` | One folder per page (dashboard, upload, results, documents, reviews) |
| `components/` | The page views and small shared UI pieces |
| `services/api.ts` | Every call to the backend API |
| `hooks/useApiData.ts` | Loading, error and polling state for API data |
| `types/api.ts` | TypeScript copies of the backend response shapes |
