# Frontend — React + TypeScript dashboard

## Setup / run

```bash
source ~/BDA-Projects/infra/env.sh     # nvm + Node 24
cd ~/BDA-Projects/sales-intelligence/frontend
npm ci
npm run dev        # http://127.0.0.1:5173
npm run typecheck
npm run build
```

Use the Linux Node from nvm. Do not run the Windows npm from `/mnt/c`.

Vite proxies `/api` to `http://127.0.0.1:8000`, so no backend URL or secret is
embedded in the bundle.

## Structure

- `src/api/client.ts` — typed fetch wrapper, query serialiser, CSV download
- `src/api/types.ts` — API response contracts
- `src/components/Layout.tsx` — sidebar, header, theme toggle, health badge
- `src/components/ui.tsx` — KPI cards, badges, table primitives, empty/error/loading
- `src/components/charts.tsx` — Recharts wrappers and shared chart styling
- `src/lib/format.ts` — money/count/date/duration formatting
- `src/lib/theme.tsx` — light/dark theme with `localStorage`
- `src/pages/` — Overview, Analytics, Transactions, Ingestion, Jobs,
  HiveAnalytics, Reports, Settings

## Data rules

Every number comes from a backend endpoint. Pages show an explicit empty state
when no processed data exists; nothing is mocked. Timestamps arrive in UTC and
are converted to browser-local time. CSV downloads call authenticated-free
backend export endpoints.
