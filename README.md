# Pressupost Generalitat Valenciana 2025

Interactive explorer for the 2025 budget of the Generalitat Valenciana.

**Budget total**: ~32.291 M€ (32,3 mil milions €)

## Contents

- `hisenda.gva.es/` — raw data mirror (HTML + PDFs)
- `SPEC.md` — detailed specification for building the web explorer
- `docs/` — (to be created) GitHub Pages static site with D3.js visualizations

## Quick start

```
deno run --allow-net --allow-read jsr:@std/http/file-server docs/
```

## Data source

https://hisenda.gva.es/auto/presupuestos/2025/index_val.html

## License

Data from Generalitat Valenciana — Conselleria d'Hisenda.
