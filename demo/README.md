# Demo evidence adapter

This package is the verified Python boundary for the official
[ShiftMem Evidence Lab](../demo-web/README.md).

- `data.py` loads only formal cells declared by the frozen evidence manifest.
  It prefers local raw-run files and, in a clean clone, reads the tracked
  release archive after verifying both the archive checksum and every
  requested file checksum.
- `export_web.py` converts the formal evidence into deterministic,
  browser-safe view models under `demo-web/public/evidence/`.
- The package does not call model providers and never modifies formal inputs.

From the repository root:

```powershell
.venv\Scripts\python.exe -m demo.export_web
cd demo-web
pnpm install
pnpm dev
```

Generated browser evidence is intentionally ignored by Git. The TypeScript
client is the only supported user interface; this package is not a second UI.
