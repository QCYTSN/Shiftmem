# ShiftMem Evidence Lab

This directory contains the official browser Demo for the frozen ShiftMem
formal experiment. It is an evidence replay and audit interface, not a live
model playground.

**Live Demo:** https://qcytsn.github.io/Shiftmem/

## Run locally

Requirements:

- Python 3.12 or newer with the repository test dependencies installed;
- Node.js 22 or newer;
- pnpm.

From the repository root:

```powershell
# Verify the manifest and export deterministic browser view models.
.venv\Scripts\python.exe -m demo.export_web

# Install and run the browser client.
cd demo-web
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://127.0.0.1:5173`.

The export works in a clean clone: when ignored raw-run files are absent, the
Python adapter verifies and reads the tracked frozen release archive without
extracting or modifying it. Generated JSON under `public/evidence/` is ignored
by Git.

## Architecture and integrity

- React and TypeScript provide the application shell.
- Custom SVG evidence tracks keep replay and cursor interaction responsive.
- Anime.js is used for restrained interface motion.
- Python is the sole evidence boundary and checks SHA-256 identities before
  emitting browser data.
- The browser never scans raw-run directories, calls model providers, or
  writes formal evidence.

See [`../demo/README.md`](../demo/README.md) for the evidence adapter and
[`../docs/demo_design_spec.md`](../docs/demo_design_spec.md) for the product
and integrity specification.

## Production check

```powershell
pnpm typecheck
pnpm build
```
