# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

A standalone Python Flask project has been added at `artifacts/bim-clash-detection` for a BIM clash detection web app. It includes a Flask backend, HTML template, CSS theme, JavaScript upload/results behavior, IFC upload storage, and PDF report export support.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)
- **BIM clash detection app**: Python Flask, HTML, CSS, JavaScript, ReportLab PDF export

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally
- `cd artifacts/bim-clash-detection && pip install -r requirements.txt` — install Flask app dependencies
- `cd artifacts/bim-clash-detection && python app.py` — run the BIM clash detection Flask app locally when ready

## BIM Clash Detection App Structure

- `artifacts/bim-clash-detection/app.py` — Flask routes for dashboard, IFC upload, clash run lookup, and PDF export
- `artifacts/bim-clash-detection/clash_detector.py` — IFC element parsing and clash result generation
- `artifacts/bim-clash-detection/pdf_export.py` — PDF report generation
- `artifacts/bim-clash-detection/templates/index.html` — dashboard markup
- `artifacts/bim-clash-detection/static/css/styles.css` — professional dark blue and white styling
- `artifacts/bim-clash-detection/static/js/app.js` — upload, results table, severity counters, and PDF download behavior
- `artifacts/bim-clash-detection/storage/uploads` — uploaded IFC files
- `artifacts/bim-clash-detection/storage/exports` — generated PDF reports

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
