# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

A Python Flask BIM clash detection web app is available from the project root for Render deployment. Root deployment files include `app.py`, `main.py`, `clash_detector.py`, `pdf_export.py`, `requirements.txt`, `render.yaml`, `runtime.txt`, `templates/`, `static/`, and `storage/`.

The BIM clash detector uses IfcOpenShell to load IFC geometry, generate model element bounding boxes, detect real geometric overlaps, and automatically ignore common intentional construction intersections: structural joints, pipe supports, rebar in concrete, door/window wall openings, and cable tray supports. The dashboard includes an Ignored Clashes Review panel so users can audit which clashes were filtered and why.

A copy of the app also remains under `artifacts/bim-clash-detection` for the existing Replit preview workflow.

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
- **BIM clash detection app**: Python Flask, HTML, CSS, JavaScript, IfcOpenShell, ReportLab PDF export, Gunicorn

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally
- `pip install -r requirements.txt` — install Render/root Flask app dependencies
- `python app.py` — run the root BIM clash detection Flask app locally
- `gunicorn app:app` — run the root app with the same WSGI target used by Render
- `cd artifacts/bim-clash-detection && python app.py` — run the artifact copy locally

## Render Deployment

- `render.yaml` defines the web service named `clashiq`.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- `runtime.txt` pins Python to `python-3.11.9`.
- `requirements.txt` includes the Render-compatible IfcOpenShell 0.7.0 direct Linux wheel URL.

## BIM Clash Detection Root App Structure

- `app.py` — Flask routes for dashboard, IFC upload, clash run lookup, and PDF export
- `main.py` — alternate Flask entrypoint for Python hosts
- `clash_detector.py` — IfcOpenShell geometry loading, overlap detection, severity classification, and smart ignore rules
- `pdf_export.py` — PDF report generation
- `requirements.txt` — Render-compatible Python dependencies, including IfcOpenShell 0.7.0 direct Linux wheel URL and Gunicorn
- `render.yaml` — Render build/start configuration
- `runtime.txt` — Python 3.11 runtime pin
- `templates/index.html` — dashboard markup with clash and ignored clash review tables
- `static/css/styles.css` — professional dark blue and white styling
- `static/js/app.js` — upload, results table, ignored results table, severity counters, and PDF download behavior
- `storage/uploads` — uploaded IFC files
- `storage/exports` — generated PDF reports

## GitHub Status

GitHub repository creation and push are blocked until GitHub authorization is completed for this project.

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
