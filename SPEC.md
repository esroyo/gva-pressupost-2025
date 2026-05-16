# Pressupost Generalitat Valenciana 2025 — Explorador Web

> **Base directory**: All file paths in this spec are relative to
> `./hisenda.gva.es/auto/presupuestos/2025/` unless otherwise noted.

## Units

All values in the source PDFs are in **milers d'euros** (thousands of euros).
For example: `32.291.432,47` milers d'euros = **€32.291M** = **~32,3 mil milions
€** (≈ 32,3 billion EUR).

> **Catalan number naming**: "mil milions" (10⁹) = English "billion". "Bilió"
> (10¹²) is NOT used here.

Throughout the web UI, display values should be formatted as:

- **Millions (M)**: `€32.291M` for top-level totals
- **Thousands (K)**: `€50.110K` for small programs
- With tooltip showing the raw value in milers d'euros

## Data Overview

| Item                                | Count | Total Size |
| ----------------------------------- | ----- | ---------- |
| HTML files (navigation + hierarchy) | 56    | 280 KB     |
| HTML hierarchy files (T2_sec*.html) | 20    | 146 KB     |
| Program-level PDFs (RPC-*)          | 20    | 636 KB     |
| Total programs (leaf nodes)         | 174   | —          |

---

## Step 1: Parse HTML Hierarchy

### Input files

20 files matching `T2_sec{XX}_VA.html` under `/auto/presupuestos/2025/`:

`01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 16, 17, 19, 20, 24, 25, 26, 28`

Sections 13, 14, 15, 18, 21, 22, 23, 27, 29, 30 do not exist (gaps in
numbering).

### Section-to-G-code mapping

G-codes (e.g. `G0109`) are NOT present in the T2_sec*.html files themselves.
They come from two sources:

1. **RPC PDF section headers** (preferred): each RPC PDF starts with
   `SECCIÓ: GXXXX - Name`. Extract the G-code from there when processing Step 2.
2. **PDF filenames in T1_i_lsec_VA.html**: the file contains links like
   `pdf/RPC-25-10-A-0011-G0109xxxx-...-VA.pdf`. Extract the G-code via regex
   `/G\d{4}/` from the matching link.

`T2_menu_epp_VA.html` maps section numbers to names only (no G-codes). Use it to
verify the section number → name mapping is consistent.

### HTML structure pattern

The hierarchy is encoded in the HTML using a sibling `<ul>` pattern. A `<li>`
element's children are in the `<ul>` that follows it as a sibling (not nested
inside it):

```html
<ul>                                    ← root container
  <li>05.- Presidència de la Generalitat              </li>  ← SECTION
  <ul>                                  ← children of section 05
    <li>01.- Sotssecretaria                            </li>  ← SA
    <ul>                                ← children of this SA
      <li>00.- Sotssecretaria                          </li>  ← DG
      <ul>                              ← children of this DG
        <li>121B00.- Alta Direcció i Serveis Generals  </li>  ← PROGRAM
        <ul><li>... PDF links ...</li></ul>                   ← (skip: PDF refs)
      </ul>
    </ul>
    <li>02.- SA de Relacions Institucionals...         </li>  ← another SA
    <ul>
      <li>01.- DG de Relacions amb Les Corts           </li>  ← DG
      <ul>
        <li>112B00.- Relacions amb Les Corts           </li>  ← PROGRAM
```

**DOM traversal algorithm**: Walk the `<ul>` tree recursively. For each `<ul>`:
iterate its child `<li>` elements. For each `<li>`, the next sibling element (if
it's a `<ul>`) contains the children of that `<li>`.

Depth in the recursive walk determines the node type:

| Depth           | Type    | `type` field | Pattern            |
| --------------- | ------- | ------------ | ------------------ |
| 0 (root `<ul>`) | section | —            | `"XX.- name"`      |
| 1               | SA      | `"sa"`       | `"XX.- name"`      |
| 2               | DG      | `"dg"`       | `"XX.- name"`      |
| 3               | program | `"program"`  | `"XXXXX00.- name"` |

Variations:

- **Without DGs**: Section → SA → Program (DG level skipped, depth 2 is program)
- **Flat**: Section → Program (both SA and DG skipped)
- **MRR section**: Pseudo-SA with name `"99.- MRR..."` containing one program

### Extraction algorithm

```
for each T2_sec{XX}_VA.html:
  1. Read file, find <!-- INICIO PARTE VARIABLE --> and
     <!-- FIN PARTE VARIABLE --> markers, extract content between them
  2. Parse the DOM tree using the sibling <ul> pattern described above
  3. For each node, extract the name by stripping the prefix:
     - Pattern "XX.- name" (sections, SA, DG): strip "XX.- " prefix
     - Pattern "XXXXX00.- name" (programs): first 7 chars = code, rest = name
     (strip "XX.- " if present on section/SA/DG names)
  4. Map section number to G-code (see mapping section above)
  5. Output hierarchical JSON fragment:
     {
       "section_code": "G0109",
       "section_name": "Educació, Cultura, Universitats i Ocupació",
       "section_number": "09",
       "children": [
         {
           "type": "sa",
           "name": "SA d'Ocupació",
           "children": [
             {
               "type": "program",
               "code": "322A00",
               "name": "Labora Servici Valencià d'Ocupació i Formació"
             },
             ...
           ]
         },
         {
           "type": "sa",
           "name": "Sotssecretaria",
           "children": [
             {
               "type": "dg",
               "name": "DG de Centres Docents",
               "children": [
                 { "type": "program", "code": "422A00", "name": "Ensenyament Primari" },
                 ...
               ]
             }
           ]
         }
       ]
     }
```

### Edge cases to handle

- Programs can appear without a parent DG (directly under SA)
- The "MRR" sub-section (99.- MRR) should be treated as a pseudo-SA
- `<li>` lines may have trailing whitespace/padding (use trim)
- Program code format: `\d{3}[A-Z0-9]\d{2}` (6 characters, e.g. `111A00`,
  `422A00`, `542C00`, `612K00`) followed by `.- name`

### Output

A JSON array of 20 section nodes, each containing the full SA/DG/Program
hierarchy tree.

Total input: ~146 KB HTML → output: ~30-40 KB JSON

> **Implementation note**: Steps 1-3 are language-agnostic. A scripting language
> like Python (with `beautifulsoup4` for HTML and `pdftotext`/`pdfplumber` for
> PDFs) or Node.js (with `jsdom` and `pdf-parse`) would work well. The key
> requirement is Catalan-locale number parsing and DOM traversal.

---

## Step 2: Extract RPC PDF Data

### Input files

20 files matching `RPC-25-10-A-00{XX}-G{XXXX}xxxx-xxxx-xxxxxx-VA.pdf` under
`/auto/presupuestos/2025/pdf/`.

Total size: ~636 KB. All are text-based PDFs generated from a tabular reporting
system.

### PDF structure

Each PDF contains a table:

```
(En milers d'euros)
PRESSUPOST DE LA GENERALITAT 2025/RESUM GENERAL PER PROGRAMES I CAPÍTOLS
SECCIÓ: G0109 - Educación, Cultura, Universidades y Empleo

Subprograma                Capítol I   Capítol II  ...  Total General
                           (personal)  (béns/c.)        de func.

315A00
Condicions de Treball i     7.905,65    3.300,00  ...   50.110,12
Administració de les
Relacions Laborals

322A00
Labora Servici Valencià     0,00        0,00      ...  228.996,25
d'Ocupació i Formació

...

TOTAL GENERAL             3.942.774,97  ...         7.599.153,47
```

Column mapping:

- Column 0: Program code (e.g., `315A00`)
- Column 1: Capítol I — Despeses de personal
- Column 2: Capítol II — Compra de béns corrents i despeses de funcionament
- Column 3: Capítol III — Despeses financeres
- Column 4: Capítol IV — Transferències corrents
- Column 5: Capítol V — Fons de contingència
- Column 6: Total operacions corrents (= sum I+V)
- Column 7: Capítol VI — Inversions reals
- Column 8: Capítol VII — Transferències de capital
- Column 9: Total operacions de capital (= VI+VII)
- Column 10: Capítol VIII — Actius financers
- Column 11: Capítol IX — Passius financers
- Column 12: Total operacions financeres (= VIII+IX)
- Column 13: Total General (= I+II+III+IV+V+VI+VII+VIII+IX)

Rows with no program code (continuation lines for multi-line program names)
should be skipped/ignored.

### Extraction algorithm

```
for each RPC PDF:
  1. Run pdftotext to extract plain text
  2. Split text into lines
  3. Scan for lines matching program code pattern: /^\d{3}[A-Z0-9]{2}00/
     Skip "TOTAL GENERAL" (it's not a program).
  4. For each code line found, extract the program block:
     a. code = the matched text (e.g. "315A00")
     b. Read the next non-empty line (the "data line"):
        - It starts with the program name text
        - Followed by space-separated numbers in Catalan locale ("1.234,56")
        - Extract name = everything before the first number token, trimmed
        - Extract all number tokens from this line into a list
     c. Continue reading subsequent non-empty lines:
        - If the line starts with a program code / "TOTAL GENERAL" → stop
        - Otherwise extract all number tokens from it, append to list
     d. You should collect 13 number tokens (columns 1-9 + subtotals)
        Map them:
          [0]=Cap.I  [1]=Cap.II  [2]=Cap.III  [3]=Cap.IV
          [4]=Cap.V   [5]=subtot.corrents  [6]=Cap.VI
          [7]=Cap.VII [8]=subtot.capital    [9]=Cap.VIII
          [10]=Cap.IX [11]=subtot.financer  [12]=Total General
        (Only use [0-4,6-7,9-10]; skip subtotals/computed columns.)
     e. Parse Catalan number format:
        remove dots (thousands), replace comma with dot, parse as float
        e.g. "1.599.951,36" → "1599951.36" → 1599951.36
     f. Skip entries where all chapter values are zero
        (these are intermediate subtotal rows that happen to match the code
        pattern — none exist, but guard against it)
  5. After all programs are extracted, find the "TOTAL GENERAL" line's
     numbers and validate: sum of all program totals should match it.

  6. Output JSON fragment:
      {
        "section_code": "G0109",
        "programs": [
          {
            "code": "315A00",
            "name": "Condicions de Treball i Administració de les Relacions Laborals",
            "chapters": {
              "1": 7905.65,   // Capítol I
              "2": 3300.00,   // Capítol II
              "3": 0,         // Capítol III
              "4": 38445.83,  // Capítol IV
              "5": 0,         // Capítol V
              "6": 0,         // Capítol VI
              "7": 458.64,    // Capítol VII
              "8": 0,         // Capítol VIII
              "9": 0          // Capítol IX
            },
            "total": 50110.12
          },
          ...
        ]
      }
```

### Number token regex

Use this regex to find Catalan-locale numbers in text:

```
/\d{1,3}(?:\.\d{3})*(?:,\d{2})?/
```

Matches: `0,00`, `23.952,81`, `1.599.951,36`, `9.000`, `5.981.611,28`.

### Edge cases

- Program name text and numbers are on the SAME line. Split using the number
  regex: everything before the first match is the name.
- Program names can span 1-3 lines (continuation lines after the data line).
  Continue appending to name until you hit a line starting with a program code,
  "TOTAL GENERAL", or a blank line.
- Numbers use Catalan locale: dots as thousands separators, comma as decimal.
- The PDF may contain page breaks/footers with stray text — ignore any line that
  doesn't contain at least one number token matching the regex above.
- Some programs may appear in section PDFs but not in the HTML hierarchy or vice
  versa — log warnings.
- Cross-check: the "TOTAL GENERAL" row should match the sum of all program
  totals in that section.

### Output

A JSON object mapping section_code → array of programs with chapter data.

Total input: ~636 KB (RPC) → output: ~60-80 KB JSON

---

## Step 3: Merge & Generate Master JSON

### Cross-reference keys

- Program code (e.g., `422A00`): primary key joining Step 1 (hierarchy) with
  Step 2 (financials)
- Section code (e.g., `G0109`): secondary key for validation

### Merge algorithm

```
hierarchy = load(Step 1 output)     // tree: section → sa → dg → program(code)
financials = load(Step 2 output)    // flat: program_code → {chapters, total}

for each section in hierarchy:
  // First pass: attach financial data
  section_total = 0
  for each program in section (recursive walk):
    if program.code in financials:
      program.chapters = financials[program.code].chapters
      program.total = financials[program.code].total
      section_total += program.total
    else:
      mark as "no data" (log warning)

  // Set section total (from sum of programs, validated against RGS later)
  section.total = section_total
  section.pct_of_total = (section_total / total_administration) × 100

  // Second pass: calculate percentages within section
  for each program in section (recursive walk):
    program.pct_of_section = (program.total / section.total) × 100

// Validate: sum of all section totals should equal total_administration
assert(sum(section.totals) == total_administration)

// Add summary data from extracted summary PDFs (see extraction below)
```

### Scope of excluded data

The following are deliberately excluded from the master JSON:

- **RMR PDF**: MRR (NextGen EU funds) detail — not part of the core budget
  structure.
- **Tom VI reports** (`informes/PUNTO1-4_VA.pdf`): narrative economic analysis,
  not structured budget data.
- **Informes PDFs** (`DANA24_VA.pdf`, `IIG_VA.pdf`, etc.): cross-cutting
  reports, not section-level data.
- **RPG (functional group) PDFs**: not implemented in the frontend views.
- **Revenue chapter data**: not implemented in the frontend views.

### Generated subdivisions (display groups)

Within each section, programs are grouped into logical clusters for human
readability. A `display_group` field on each program node and a `display_groups`
lookup table at the section level define these clusters:

```json
{
  "section_code": "G0109",
  "display_groups": {
    "EDU_ADMIN": { "label": "Administració Educativa", "order": 0 },
    "EDU_SCHOOL": { "label": "Educació escolar", "order": 1 },
    "EDU_UNI": { "label": "Universitats i Investigació", "order": 2 },
    "EDU_WORK": { "label": "Ocupació i Treball", "order": 3 },
    "EDU_CULTURE": { "label": "Cultura", "order": 4 },
    "EDU_MRR": { "label": "MRR", "order": 5 }
  },
  "mapping": {
    "421A00": "EDU_ADMIN",
    "421D00": "EDU_ADMIN",
    ...
    "422A00": "EDU_SCHOOL",
    "422B00": "EDU_SCHOOL",
    ...
    "422M00": "EDU_MRR"
  }
}
```

The web UI uses `display_group` for group-based coloring when zoomed into a
section. A legend shows the group colors. All 20 sections have display groups
defined in `step3_merge.py`:

| Section                           | Groups                                                                           | Programs |
| --------------------------------- | -------------------------------------------------------------------------------- | -------- |
| G0101 Les Corts                   | Activitat Legislativa, Control i Fiscalització                                   | 2        |
| G0102 Sindicatura                 | Control Extern                                                                   | 1        |
| G0103 Consell Valencià de Cultura | Assessorament Cultural                                                           | 1        |
| G0104 Consell Jurídic Consultiu   | Alt Assessorament                                                                | 1        |
| G0105 Presidència                 | Direcció, Coordinació, Territori, Comunicació, Assessorament, Esports, Anàlisi   | 23       |
| G0106 Hisenda                     | Direcció, Política Financera, Tributs, Digitalització, Economia, MRR             | 23       |
| G0107 Justícia                    | Direcció, Justícia, Electorals, Concòrdia, Ciutadania, Inspecció, Funció Pública | 9        |
| G0108 Medi Ambient                | Direcció, Urbanisme, Medi Natural, Incendis, Infraestructures, Ports             | 12       |
| G0109 Educació                    | Administració, Educació escolar, Universitats, Ocupació, Cultura, MRR            | 26       |
| G0110 Sanitat                     | Direcció, Hospitalària, Primària, Salut Pública, Informació, MRR                 | 22       |
| G0111 Innovació                   | Direcció, Digital, R+D, Indústria, Consum, Comerç, Turisme, MRR                  | 12       |
| G0112 Agricultura                 | Direcció, Agricultura, Aigua, Rural, PAC, Agroalimentària, Pesca                 | 10       |
| G0116 Serveis Socials             | Direcció, Igualtat, Inclusió, Cooperació, Habitatge                              | 17       |
| G0117 AVL                         | Investigació Lingüística                                                         | 1        |
| G0119 Deute                       | Servei del Deute                                                                 | 1        |
| G0120 Despeses Diverses           | RTVV, Despeses Diverses                                                          | 2        |
| G0124 CES                         | Assessorament Social i Econòmic                                                  | 1        |
| G0125 Síndic                      | Defensa dels Drets                                                               | 1        |
| G0126 Recuperació                 | Direcció, Planificació, Catàstrofes                                              | 5        |
| G0128 Emergències                 | Direcció, Seguretat, Incendis, Innovació                                         | 4        |

### Master JSON structure

```json
{
  "meta": {
    "title": "Pressupost Generalitat Valenciana 2025",
    "year": 2025,
    "language": "ca",
    "total_administration": 32291432.47,
    "total_consolidated": 34202706.82,
    "currency": "EUR",
    "unit": "milers d'euros",
    "last_updated": "2025-05-16",
    "source_url": "https://hisenda.gva.es/auto/presupuestos/2025/index_val.html",
    "source_base": "https://hisenda.gva.es/auto/presupuestos/2025/",
    "source_pdf_base": "https://hisenda.gva.es/auto/presupuestos/2025/pdf/"
  },
  "chapter_labels": {
    "1": "Personal",
    "2": "Béns i serveis",
    ...
  },
  "chapter_colors": {
    "1": "#4e79a7",
    ...
  },
  "summaries": {
    "by_section": [ ... ],    // Flat table: all sections with totals
    "by_chapter": [ ... ]     // Flat table: all chapters with totals
  },
  "sections": [
    {
      "section_code": "G0109",
      "number": "09",
      "name": "Educació, Cultura, Universitats i Ocupació",
      "total": 7599153.47,
      "pct_of_total": 23.5,
      "chapters": { "1": 3942774.97, "2": 433346.29, ... },
      "display_groups": {
        "EDU_ADMIN": { "label": "Administració Educativa", "order": 0 },
        ...
      },
      "source_pdf": "RPC-25-10-A-0011-G0109xxxx-xxxx-xxxxxx-VA.pdf",
      "source_html": "T2_sec09_VA.html",
      "children": [
        {
          "type": "sa",
          "name": "SA d'Ocupació",
          "id": "G0109.sa_ocupacio",
          "total": 291015.10,
          "pct_of_parent": 3.8,
          "children": [
            {
              "type": "program",
              "code": "322A00",
              "name": "Labora Servici Valencià d'Ocupació i Formació",
              "id": "G0109.322A00",
              "total": 228996.25,
              "pct_of_parent": 78.7,
              "chapters": { "4": 217131.54, "6": 0, "7": 11864.71 },
              "display_group": "EDU_WORK",
              "source_pdfs": [
                "pdf/FP1-25-10-A-0001-G01090400-9999-322A00-VA.pdf",
                ...
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Key design decisions

- **IDs**: Every node gets a unique `id` (e.g., `G0109.sa_ocupacio`,
  `G0109.322A00`) for D3 click/highlight
- **Percentages**: Every node has `pct_of_parent` (vs direct parent) and nodes
  at section level have `pct_of_total`
- **Source links**: Program nodes include links to their FP1-FP9 PDFs
  (constructed from the known filename pattern) as an array of URL strings.
  SA/DG nodes link to the section HTML
- **Chapters**: Include all chapter values (including zero) for consistent bar
  chart rendering
- **display_groups**: Section-level lookup table. Each program carries its group
  key as `display_group`. The frontend uses this for per-section group coloring
  and legend display

### Validation

- Sum of all section totals = `total_administration` (32.291.432,47)
- Sum of all program chapters within a section = section total
- Cross-check against RGS and PCS summary PDFs

---

## Step 4: Build HTML + D3.js Frontend

### Architecture

Single-page application. Zero server dependencies, no build step, no npm. One
`index.html` file with embedded CSS and a local copy of D3.js.

### Libraries

- **D3.js v7.9.0** (local file `docs/d3.min.js`): treemap, sunburst, zoomable
  icicle layouts.
- No frameworks (React, Vue, etc.) — keep it simple, static, and fast

### Critical D3.js minified-version caveats

The minified D3 v7 bundle at `docs/d3.min.js` differs from the standard (dev)
build in ways that affect hierachical layouts:

1. **`d.sum()` accessor**: The minified build passes `n.data` (the data object,
   not the hierarchy node) to the sum accessor callback. This means
   `d => d.total` works on the data object's fields directly, not via
   `d.data.total`. Access properties as `d.total` not `d.data.total`.

2. **Treemap/partition on subtrees**: The minified D3 uses
   `paddingStack[node.depth]` internally and throws when `node.depth` exceeds
   the padding array length for depth > 0 subtrees. Fix: wrap the subtree in a
   dummy root at depth 0, run the layout on the wrapper, then copy the
   coordinates back to the real nodes.

### Page layout

```
┌──────────────────────────────────────────────────────────┐
│  Header: "Pressupost Generalitat Valenciana 2025" | €32.291M │
├──────────────────────────────────────────────────────────┤
│  Controls: [Treemap] [Icicle] [Sunburst] | [Per seccions ▼] │
│  Search: [______________]  |  [↑ Nivell superior]       │
├──────────────────────────────────────────────────────────┤
│  Breadcrumb: Generalitat › G0109 Sanitat › ...          │
├──────────────────────────────────────────────────────────┤
│     MAIN VIZ AREA (D3 chart — treemap/icicle/sunburst)  │
│                                                          │
│  Legend (bottom-left, on section drill-down):            │
│  ┌──────────────┐                                        │
│  │ Grups        │                                        │
│  │ ● Direcció   │                                        │
│  │ ● Hospitalària  │                                     │
│  │ ● Primària   │                                        │
│  └──────────────┘                                        │
├──────────────────────────────────────────────────────────┤
│  Detail panel (right sidebar, shown on click):           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  G0110 – Sanitat                          │  │
│  │  28.45% del pressupost total                     │  │
│  │  €9.187,0M                                       │  │
│  │  9.186.974 milers d'euros                       │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ ████████████████████████ 48% Personal      │  │  │
│  │  │ ██████████████          31% Béns i serveis │  │  │
│  │  │ ██████                  15% Transf.corrents│  │  │
│  │  │ ██                       5% Inversions     │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  PDF: FP1-25-10-A-0002-...pdf                   │  │
│  │  RPC - Sanitat · Estructura de programes        │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Chart types

Three chart types driven by the same hierarchical data:

- **Treemap** (default): rectangles sized by `total`. Click to zoom into
  subtree.
- **Icicle**: top-down horizontal bars. Click to drill down.
- **Sunburst**: radial partition layout. Click segment to zoom.

All three use `d3.hierarchy()` + either `d3.treemap()` or `d3.partition()`.

### Modes

- **Per seccions** (default): the administrative hierarchy (section → SA → DG →
  program). Group colors and legend appear when zoomed into a section with
  `display_groups`.
- **Per capítols**: rebuilds the tree with chapter as root, then section → SA →
  DG → program, filtered to programs with spending in the selected chapter. Uses
  `buildChapterHierarchy(data)`.

### Interactions

- **Click node**: Drill into its subtree. Update detail panel. Update
  breadcrumb. Show "Nivell superior" button and group legend.
- **Click empty space / "Nivell superior"**: Zoom out one level.
- **Hover**: Tooltip with name, amount, percentage.
- **Breadcrumb**: Click any ancestor to jump back up.
- **Search**: Filter nodes by name or code (min 2 chars). Matches get a black
  outline highlight (`3px solid #000` + white inner shadow).
- **View switcher**: Toggle treemap/icicle/sunburst.
- **Mode switcher**: Toggle "Per seccions" / "Per capítols".
- **Responsive**: SVG resizes to fit container (`ResizeObserver`).

### Detail panel (right sidebar)

Shows on node click:

- Node code + name
- If program: display group label (if available)
- Total amount + percentage
- Horizontal chapter breakdown bars (color-coded, sorted by size)
- Source links:
  - Program: FP1-FP9 PDFs linked individually
  - Section: RPC PDF + program structure HTML
  - Always: link to main budget index

### Color palette

- **By section**: `d3.schemeTableau10` ordinal scale (cycles for 20 sections)
- **By economic chapter**: 9 fixed colors from `CHAPTER_COLORS`:
  - 1 (Personal): `#4e79a7` (blue)
  - 2 (Béns i serveis): `#59a14f` (green)
  - 3 (Financeres): `#b07aa1` (purple)
  - 4 (Transferències corrents): `#f28e2b` (orange)
  - 5 (Fons de contingència): `#e15759` (red)
  - 6 (Inversions reals): `#76b7b2` (teal)
  - 7 (Transferències de capital): `#edc948` (yellow)
  - 8 (Actius financers): `#af7aa1` (mauve)
  - 9 (Passius financers): `#ff9da7` (pink)
- **By display group (section drill-down)**: Per-section colors derived from the
  section's Tableau10 base hue. Groups are spread evenly across a 280° hue range
  centered on the base hue, with fixed saturation 0.55 and lightness 0.58. Only
  active when zoomed into a section that has `display_groups` defined.

### File structure

```
/docs/
  index.html    ← Main page (HTML + inline CSS + JS)
  d3.min.js     ← D3.js v7 UMD bundle (minified — see caveats above)
  data.json     ← Master JSON from Step 3 (214 KB)
```

---

## Step 5: Deploy (GitHub Pages)

```
/docs/
  index.html
  d3.min.js
  data.json
```

1. Push the repo to GitHub
2. Go to Settings → Pages → Source: "Deploy from a branch"
3. Branch: `main`, folder: `/docs`
4. The site will be live at `https://{user}.github.io/{repo}/`

Alternatively, preview locally with:

```
deno run --allow-net --allow-read jsr:@std/http/file-server docs/
```

> **CORS note**: `fetch()` loads `data.json` via HTTP. Opening `docs/index.html`
> directly with `file://` protocol will fail due to CORS. Always use a local
> HTTP server (like Deno above) for preview.

### Maintenance

- Data is for 2025 only. To add 2026: repeat Steps 1-3 with new year's data,
  regenerate `data.json`
- The web frontend is year-agnostic — just swap the JSON file

---

## Total Token/Time Estimate for Execution

| Step                | Tokens     | Description                                                              |
| ------------------- | ---------- | ------------------------------------------------------------------------ |
| 1. Parse HTML       | ~30K       | Read 20 HTML files, extract hierarchy, output JSON                       |
| 2. Extract PDFs     | ~200K      | Run pdftotext on 20 RPC PDFs, parse program rows, output JSON            |
| 3. Merge & generate | ~80K       | Join hierarchies + financials, add metadata, validate, write master JSON |
| 4. Build web UI     | Write code | ~520 lines of HTML/CSS/JS, D3 treemap/icicle/sunburst, chapter view      |
| 5. Deploy           | Trivial    | Copy files                                                               |
| **Total tokens**    | **~310K**  | For data extraction (Steps 1-3). Step 4 is code writing.                 |

The most expensive sub-step is parsing the 20 RPC PDFs (~200K tokens) because
each needs to be read and its tabular data extracted. But at ~200K tokens, this
is still very cheap.
