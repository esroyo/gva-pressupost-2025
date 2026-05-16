# AGENTS.md — Pressupost GV 2025

## Project structure

- `docs/` — GitHub Pages static site (index.html + d3.min.js + data.json)
- `hisenda.gva.es/` — local mirror of source data (HTML + PDFs)
- `step1_parse_html.py` — extracts hierarchy from T2_sec*.html →
  `step1_hierarchy.json`
- `step2_parse_pdfs.py` — extracts financials via pdftotext →
  `step2_financials.json`
- `step3_merge.py` — joins hierarchy + financials → `docs/data.json`
- `SPEC.md` — full specification document

## Key facts

- All values in **milers d'euros** (thousands of euros)
- Catalan locale numbers: dots = thousands separator, comma = decimal (e.g.,
  `1.599.951,36`)
- ISO language code for Valencian: `"ca"` (not `"va"`)
- **Total administration budget**: 32.291.432,47 K€ (≈ 32.291M €)
- **Total consolidated**: 34.202.706,82 K€

## Program code pattern

Program codes are 6 characters: `\d{3}[A-Z0-9]\d{2}` (not `\d{3}[A-Z0-9]{2}00`).
Examples: `111A00`, `422A00`, `542C00`, `612K00`.

## Build commands

- Parse HTML hierarchy: `python3 step1_parse_html.py`
- Parse PDF financials: `python3 step2_parse_pdfs.py`
- Generate master JSON: `python3 step3_merge.py`
- Preview locally:
  `deno run --allow-net --allow-read jsr:@std/http/file-server docs/`
- Full pipeline:
  `python3 step1_parse_html.py && python3 step2_parse_pdfs.py && python3 step3_merge.py`

## HTML hierarchy parsing

- Uses sibling `<ul>` pattern: a `<li>`'s children are in the `<ul>` that
  follows it as a sibling
- A `<li>` can have multiple consecutive `<ul>` siblings — all are merged as
  children
- Section numbers: 01-12, 16, 17, 19, 20, 24, 25, 26, 28 (gaps in numbering)
- G-code mapping extracted from `T1_i_lsec_VA.html`

## PDF parsing

- Use `pdftotext -layout` for clean columnar output
- The name and numbers share the same line; split by detecting Catalan-locale
  numbers from the right
- Numbers require `.` (thousands) or `,` (decimal) to avoid matching digits in
  program names
- 13 number columns per program row, mapped to chapters 1-9 (skip subtotals)

## Frontend

- D3.js v7.9.0, local copy in `docs/d3.min.js`
- Treemap default view with zoomable drill-down
- Click node → zoom into its subtree; click empty space → zoom out
- Detail panel shows chapter breakdown bars + source PDF links
- Search filters by name/code
