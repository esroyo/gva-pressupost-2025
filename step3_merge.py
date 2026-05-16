import json, re
from pathlib import Path
from bs4 import BeautifulSoup, Tag

BASE = Path("hisenda.gva.es/auto/presupuestos/2025")
HIERARCHY = json.load(Path("step1_hierarchy.json").open())
FINANCIALS = json.load(Path("step2_financials.json").open())
OUT = Path("docs/data.json")

TOTAL_ADMINISTRATION = 32291432.47  # validated from RPC totals


# ── Extract FP* PDF links from T2_sec*.html ──
def extract_program_pdfs():
    """Returns dict: section_code → { program_code: [pdf_urls] }"""
    result = {}
    for fp in sorted(BASE.glob("T2_sec??_VA.html")):
        html = fp.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        root_ul = soup.find("ul")
        if not root_ul:
            continue
        section_code = None
        # Find the RPC link for section code
        for a in root_ul.find_all("a", href=True):
            m = re.search(r"G(\d{4})", a["href"])
            if m:
                section_code = f"G{m.group(1)}"
                break
        if not section_code:
            continue

        pdfs = {}
        for li in root_ul.find_all("li"):
            text = li.get_text(strip=True)
            code_m = re.match(r"^(\d{3}[A-Z0-9]\d{2})\.\s*-\s*(.+)", text)
            if not code_m:
                continue
            prog_code = code_m.group(1)
            # Find FP* links in this li's sibling/child ul
            # The program li's children are in the next ul sibling
            next_ul = li.find_next_sibling("ul")
            if next_ul:
                fp_links = []
                for a in next_ul.find_all("a", href=True):
                    href = a["href"]
                    if re.match(r"FP\d-", href.split("/")[-1]):
                        fp_links.append(href)
                if fp_links:
                    pdfs[prog_code] = fp_links

        if pdfs:
            result[section_code] = pdfs

    return result


PROGRAM_PDFS = extract_program_pdfs()
print(f"Program PDFs extracted for {len(PROGRAM_PDFS)} sections")


# ── Display groups lookup ──
DISPLAY_GROUPS = {
    "G0101": {
        "groups": {
            "LEG_ACTIVITY": {"label": "Activitat Legislativa", "order": 0},
            "LEG_AUDIT": {"label": "Control i Fiscalització", "order": 1},
        },
        "mapping": {
            "111A00": "LEG_ACTIVITY",
            "111J00": "LEG_AUDIT",
        },
    },
    "G0102": {
        "groups": {
            "AUDIT": {"label": "Control Extern", "order": 0},
        },
        "mapping": {
            "111B00": "AUDIT",
        },
    },
    "G0103": {
        "groups": {
            "CVC_CULTURE": {"label": "Assessorament Cultural", "order": 0},
        },
        "mapping": {
            "111C00": "CVC_CULTURE",
        },
    },
    "G0104": {
        "groups": {
            "CJC_ADV": {"label": "Alt Assessorament", "order": 0},
        },
        "mapping": {
            "111F00": "CJC_ADV",
        },
    },
    "G0105": {
        "groups": {
            "PRES_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "PRES_COORD": {"label": "Coordinació i Relacions", "order": 1},
            "PRES_TERRIT": {"label": "Administració Local i Territori", "order": 2},
            "PRES_COM": {"label": "Comunicació i Premsa", "order": 3},
            "PRES_LEGAL": {"label": "Assessorament i Control", "order": 4},
            "PRES_SPORT": {"label": "Esports", "order": 5},
            "PRES_POLICY": {"label": "Anàlisi i Polítiques Públiques", "order": 6},
        },
        "mapping": {
            "121B00": "PRES_DIR",
            "126C00": "PRES_DIR",
            "121L00": "PRES_DIR",
            "121N00": "PRES_DIR",
            "111G00": "PRES_DIR",
            "111L00": "PRES_DIR",
            "121J00": "PRES_DIR",
            "112A00": "PRES_COORD",
            "112B00": "PRES_COORD",
            "112C00": "PRES_COORD",
            "112D00": "PRES_COORD",
            "112G00": "PRES_COORD",
            "112H00": "PRES_COORD",
            "112J00": "PRES_COORD",
            "125A00": "PRES_TERRIT",
            "125B00": "PRES_TERRIT",
            "462A00": "PRES_COM",
            "462B00": "PRES_COM",
            "112I00": "PRES_COM",
            "126A00": "PRES_LEGAL",
            "126B00": "PRES_LEGAL",
            "457A00": "PRES_SPORT",
            "111D00": "PRES_POLICY",
        },
    },
    "G0106": {
        "groups": {
            "HIS_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "HIS_FIN": {"label": "Política Financera i Fons", "order": 1},
            "HIS_TRIB": {"label": "Tributs i Pressupostos", "order": 2},
            "HIS_DIG": {"label": "Digitalització i Sistemes", "order": 3},
            "HIS_ECO": {"label": "Economia i Estadística", "order": 4},
            "HIS_MRR": {"label": "MRR", "order": 5},
        },
        "mapping": {
            "611A00": "HIS_DIR",
            "611B00": "HIS_DIR",
            "612B00": "HIS_FIN",
            "631A00": "HIS_FIN",
            "631B00": "HIS_FIN",
            "615B00": "HIS_FIN",
            "613A00": "HIS_TRIB",
            "613B00": "HIS_TRIB",
            "612E00": "HIS_TRIB",
            "612D00": "HIS_TRIB",
            "612A00": "HIS_FIN",
            "612C00": "HIS_TRIB",
            "612G00": "HIS_DIG",
            "612H00": "HIS_DIG",
            "612I00": "HIS_DIG",
            "121F00": "HIS_DIG",
            "121G00": "HIS_DIG",
            "615A00": "HIS_ECO",
            "615C00": "HIS_ECO",
            "551A00": "HIS_ECO",
            "111H00": "HIS_ECO",
            "612K00": "HIS_MRR",
            "121M00": "HIS_MRR",
        },
    },
    "G0107": {
        "groups": {
            "JUS_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "JUS_ADMIN": {"label": "Administració de Justícia", "order": 1},
            "JUS_ELECT": {"label": "Processos Electorals", "order": 2},
            "JUS_CONC": {"label": "Concòrdia i Autogovern", "order": 3},
            "JUS_CITIZEN": {"label": "Atenció a la Ciutadania", "order": 4},
            "JUS_INSP": {"label": "Inspecció i Control", "order": 5},
            "JUS_CIVIL": {"label": "Funció Pública i Formació", "order": 6},
        },
        "mapping": {
            "141B00": "JUS_DIR",
            "141A00": "JUS_ADMIN",
            "112F00": "JUS_ADMIN",
            "462C00": "JUS_ELECT",
            "126D00": "JUS_CONC",
            "121A00": "JUS_CITIZEN",
            "121K00": "JUS_INSP",
            "121C00": "JUS_CIVIL",
            "121D00": "JUS_CIVIL",
        },
    },
    "G0108": {
        "groups": {
            "ENV_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "ENV_URBAN": {"label": "Urbanisme i Territori", "order": 1},
            "ENV_NATURE": {"label": "Medi Natural i Ambiental", "order": 2},
            "ENV_FIRE": {"label": "Prevenció d'Incendis", "order": 3},
            "ENV_INFRA": {"label": "Infraestructures i Transport", "order": 4},
            "ENV_PORTS": {"label": "Ports, Aeroports i Costes", "order": 5},
        },
        "mapping": {
            "511A00": "ENV_DIR",
            "432A00": "ENV_URBAN",
            "442E00": "ENV_URBAN",
            "442A00": "ENV_NATURE",
            "442B00": "ENV_NATURE",
            "442C00": "ENV_NATURE",
            "442D00": "ENV_NATURE",
            "442F00": "ENV_FIRE",
            "513A00": "ENV_INFRA",
            "514A00": "ENV_PORTS",
            "513B00": "ENV_INFRA",
            "513M00": "ENV_INFRA",
        },
    },
    "G0109": {
        "groups": {
            "EDU_ADMIN": {"label": "Administració Educativa", "order": 0},
            "EDU_SCHOOL": {"label": "Educació escolar", "order": 1},
            "EDU_UNI": {"label": "Universitats i Investigació", "order": 2},
            "EDU_WORK": {"label": "Ocupació i Treball", "order": 3},
            "EDU_CULTURE": {"label": "Cultura", "order": 4},
            "EDU_MRR": {"label": "MRR", "order": 5},
        },
        "mapping": {
            "421A00": "EDU_ADMIN",
            "421D00": "EDU_ADMIN",
            "421B00": "EDU_ADMIN",
            "421F00": "EDU_ADMIN",
            "421G00": "EDU_ADMIN",
            "421C00": "EDU_ADMIN",
            "421H00": "EDU_SCHOOL",
            "422I00": "EDU_SCHOOL",
            "422A00": "EDU_SCHOOL",
            "422B00": "EDU_SCHOOL",
            "422C00": "EDU_SCHOOL",
            "422H00": "EDU_SCHOOL",
            "422F00": "EDU_SCHOOL",
            "422D00": "EDU_SCHOOL",
            "421E00": "EDU_SCHOOL",
            "422E00": "EDU_UNI",
            "422G00": "EDU_UNI",
            "542C00": "EDU_UNI",
            "322A00": "EDU_WORK",
            "315A00": "EDU_WORK",
            "322D00": "EDU_WORK",
            "453B00": "EDU_CULTURE",
            "452A00": "EDU_CULTURE",
            "453A00": "EDU_CULTURE",
            "454A00": "EDU_CULTURE",
            "422M00": "EDU_MRR",
        },
    },
    "G0110": {
        "groups": {
            "SAN_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "SAN_HOSP": {"label": "Atenció Hospitalària", "order": 1},
            "SAN_PRIM": {"label": "Atenció Primària i Centres", "order": 2},
            "SAN_PUBLIC": {"label": "Salut Pública", "order": 3},
            "SAN_INFO": {"label": "Informació Sanitària", "order": 4},
            "SAN_MRR": {"label": "MRR", "order": 5},
        },
        "mapping": {
            "411A00": "SAN_DIR",
            "411G00": "SAN_DIR",
            "411C00": "SAN_DIR",
            "411D00": "SAN_DIR",
            "411B00": "SAN_DIR",
            "411H00": "SAN_DIR",
            "411E00": "SAN_DIR",
            "411F00": "SAN_DIR",
            "412B22": "SAN_HOSP",
            "412B25": "SAN_HOSP",
            "412B24": "SAN_HOSP",
            "412B26": "SAN_HOSP",
            "412B28": "SAN_HOSP",
            "412B23": "SAN_HOSP",
            "412B27": "SAN_HOSP",
            "412B21": "SAN_PRIM",
            "412A00": "SAN_PRIM",
            "413A00": "SAN_PUBLIC",
            "313B00": "SAN_PUBLIC",
            "412B29": "SAN_INFO",
            "413M00": "SAN_MRR",
            "412M00": "SAN_MRR",
        },
    },
    "G0111": {
        "groups": {
            "INN_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "INN_DIGITAL": {"label": "Societat Digital", "order": 1},
            "INN_RD": {"label": "R+D+i", "order": 2},
            "INN_IND": {"label": "Indústria i Energia", "order": 3},
            "INN_CONSUM": {"label": "Protecció de Persones Consumidores", "order": 4},
            "INN_COM": {"label": "Comerç i Emprenedoria", "order": 5},
            "INN_TOUR": {"label": "Turisme", "order": 6},
            "INN_MRR": {"label": "MRR", "order": 7},
        },
        "mapping": {
            "721A00": "INN_DIR",
            "121H00": "INN_DIGITAL",
            "542D00": "INN_RD",
            "542F00": "INN_RD",
            "722A00": "INN_IND",
            "731A00": "INN_IND",
            "443A00": "INN_CONSUM",
            "761A00": "INN_COM",
            "322B00": "INN_COM",
            "762A00": "INN_COM",
            "751A00": "INN_TOUR",
            "542M00": "INN_MRR",
        },
    },
    "G0112": {
        "groups": {
            "AGR_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "AGR_AGRI": {"label": "Agricultura i Producció", "order": 1},
            "AGR_WATER": {"label": "Recursos Hidràulics", "order": 2},
            "AGR_RD": {"label": "Desenvolupament Rural i I+D+i", "order": 3},
            "AGR_PAC": {"label": "Política Agrària Comú", "order": 4},
            "AGR_FOOD": {"label": "Indústria Agroalimentària", "order": 5},
            "AGR_FISH": {"label": "Pesca", "order": 6},
        },
        "mapping": {
            "711A00": "AGR_DIR",
            "531A00": "AGR_AGRI",
            "714B00": "AGR_AGRI",
            "714D00": "AGR_AGRI",
            "512A00": "AGR_WATER",
            "542B00": "AGR_RD",
            "542E00": "AGR_RD",
            "714C00": "AGR_PAC",
            "714F00": "AGR_FOOD",
            "714A00": "AGR_FISH",
        },
    },
    "G0116": {
        "groups": {
            "SS_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "SS_EQUAL": {"label": "Igualtat i Diversitat", "order": 1},
            "SS_SOCIAL": {"label": "Inclusió i Serveis Socials", "order": 2},
            "SS_COOP": {"label": "Cooperació Internacional", "order": 3},
            "SS_HOUSING": {"label": "Habitatge", "order": 4},
        },
        "mapping": {
            "311A00": "SS_DIR",
            "323A00": "SS_EQUAL",
            "313H00": "SS_SOCIAL",
            "323B00": "SS_EQUAL",
            "313F00": "SS_SOCIAL",
            "313G00": "SS_SOCIAL",
            "134A00": "SS_COOP",
            "313E00": "SS_SOCIAL",
            "313C00": "SS_SOCIAL",
            "313D00": "SS_SOCIAL",
            "313J00": "SS_SOCIAL",
            "313I00": "SS_SOCIAL",
            "313K00": "SS_SOCIAL",
            "431H00": "SS_HOUSING",
            "431I00": "SS_HOUSING",
            "313M00": "SS_SOCIAL",
            "323M00": "SS_EQUAL",
        },
    },
    "G0117": {
        "groups": {
            "AVL_LING": {
                "label": "Investigació i Normalització Lingüística",
                "order": 0,
            },
        },
        "mapping": {
            "541A00": "AVL_LING",
        },
    },
    "G0119": {
        "groups": {
            "DEBT": {"label": "Servei del Deute", "order": 0},
        },
        "mapping": {
            "011A00": "DEBT",
        },
    },
    "G0120": {
        "groups": {
            "MISC_MEDIA": {"label": "Ràdio Televisió Pública", "order": 0},
            "MISC_EXP": {"label": "Despeses Diverses", "order": 1},
        },
        "mapping": {
            "462D00": "MISC_MEDIA",
            "612F00": "MISC_EXP",
        },
    },
    "G0124": {
        "groups": {
            "CES_ADV": {"label": "Assessorament Social i Econòmic", "order": 0},
        },
        "mapping": {
            "111I00": "CES_ADV",
        },
    },
    "G0125": {
        "groups": {
            "OMB_DEF": {"label": "Defensa dels Drets Fonamentals", "order": 0},
        },
        "mapping": {
            "111E00": "OMB_DEF",
        },
    },
    "G0126": {
        "groups": {
            "REC_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "REC_PLAN": {"label": "Planificació de la Recuperació", "order": 1},
            "REC_CATA": {"label": "Protecció davant Catàstrofes", "order": 2},
        },
        "mapping": {
            "120A00": "REC_DIR",
            "120B00": "REC_PLAN",
            "120C00": "REC_PLAN",
            "120D00": "REC_PLAN",
            "442G00": "REC_CATA",
        },
    },
    "G0128": {
        "groups": {
            "EMER_DIR": {"label": "Direcció i Serveis Generals", "order": 0},
            "EMER_SEC": {"label": "Seguretat i Protecció Civil", "order": 1},
            "EMER_FIRE": {"label": "Emergències i Extinció d'Incendis", "order": 2},
            "EMER_INN": {"label": "Innovació en Emergències", "order": 3},
        },
        "mapping": {
            "221D00": "EMER_DIR",
            "221A00": "EMER_SEC",
            "221C00": "EMER_FIRE",
            "221E00": "EMER_INN",
        },
    },
}

CHAPTER_LABELS = {
    "1": "Personal",
    "2": "Béns i serveis",
    "3": "Financeres",
    "4": "Transferències corrents",
    "5": "Fons de contingència",
    "6": "Inversions reals",
    "7": "Transferències de capital",
    "8": "Actius financers",
    "9": "Passius financers",
}

CHAPTER_COLORS = {
    "1": "#4e79a7",
    "2": "#59a14f",
    "3": "#b07aa1",
    "4": "#f28e2b",
    "5": "#e15759",
    "6": "#76b7b2",
    "7": "#edc948",
    "8": "#af7aa1",
    "9": "#ff9da7",
}


def attach_financials(node, fin_data, section_total):
    """Recursively attach financial data to hierarchy nodes."""
    if node.get("type") == "program":
        code = node["code"]
        fp = fin_data.get(code)
        if fp:
            node["total"] = fp["total"]
            node["chapters"] = fp["chapters"]
            node["pct_of_parent"] = (
                round((fp["total"] / section_total * 100), 1) if section_total else 0
            )
        else:
            node["total"] = 0
            node["chapters"] = {}
            node["pct_of_parent"] = 0

    total = 0
    for child in node.get("children", []):
        child_total = attach_financials(child, fin_data, section_total)
        total += child_total

    if node.get("type") in ("sa", "dg", "section"):
        # For non-program nodes, sum children totals
        if not node.get("children"):  # leaf but not program (shouldn't happen)
            node["total"] = 0
        else:
            node["total"] = total

    return node.get("total", 0) or total


def build_id(section_code, node, parent_id=""):
    """Generate unique IDs for each node."""
    if node.get("type") == "section":
        node["id"] = section_code
    elif node.get("type") == "program":
        node["id"] = f"{section_code}.{node['code']}"
    elif node.get("type") == "sa":
        safe = re.sub(r"[^a-z0-9]", "_", node["name"].lower())[:20]
        node["id"] = f"{section_code}.sa_{safe}"
    elif node.get("type") == "dg":
        safe = re.sub(r"[^a-z0-9]", "_", node["name"].lower())[:20]
        node["id"] = f"{section_code}.dg_{safe}"

    for child in node.get("children", []):
        build_id(section_code, child)


def compute_pct_of_parent(node, parent_total=0):
    """Compute percentages for each node relative to its parent."""
    if node.get("type") != "section" and parent_total:
        node["pct_of_parent"] = (
            round((node.get("total", 0) / parent_total * 100), 1) if parent_total else 0
        )

    children = node.get("children", [])
    node_total = node.get("total", 0)
    for child in children:
        compute_pct_of_parent(child, node_total)


def add_display_groups(section_node, section_code):
    """Add display groups from lookup table."""
    dg = DISPLAY_GROUPS.get(section_code)
    if not dg:
        return

    section_node["display_groups"] = dg["groups"]

    def walk(node):
        if node.get("type") == "program":
            code = node["code"]
            group_key = dg["mapping"].get(code)
            if group_key:
                node["display_group"] = group_key
        for child in node.get("children", []):
            walk(child)

    walk(section_node)


def add_source_pdfs(section_node, section_code):
    """Add source PDF links to program nodes."""
    sec_pdfs = PROGRAM_PDFS.get(section_code, {})

    def walk(node):
        if node.get("type") == "program":
            code = node["code"]
            fps = sec_pdfs.get(code)
            if fps:
                node["source_pdfs"] = fps
        for child in node.get("children", []):
            walk(child)

    walk(section_node)


# ── Build master ──
fin_by_code = {}
for sc, data in FINANCIALS["sections"].items():
    for p in data["programs"]:
        fin_by_code[p["code"]] = p

sections_out = []

for sec in HIERARCHY["sections"]:
    sc = sec["section_code"]
    sec_fin = FINANCIALS["sections"].get(sc, {})
    sec_progs = {p["code"]: p for p in sec_fin.get("programs", [])}

    # Attach financials to hierarchy
    sec_total = attach_financials(sec, sec_progs, 0)

    # Set section total
    sec["total"] = sec_total
    sec["pct_of_total"] = round((sec_total / TOTAL_ADMINISTRATION * 100), 2)

    # Get chapter-level breakdown for section
    section_chapters = {}

    def sum_chapters(node):
        if node.get("type") == "program":
            for k, v in node.get("chapters", {}).items():
                section_chapters[k] = section_chapters.get(k, 0) + v
        for c in node.get("children", []):
            sum_chapters(c)

    sum_chapters(sec)
    sec["chapters"] = dict(sorted(section_chapters.items()))

    # Generate IDs
    build_id(sc, sec)

    # Compute percentages
    compute_pct_of_parent(sec, TOTAL_ADMINISTRATION)

    # Add display groups
    add_display_groups(sec, sc)

    # Add source PDFs
    add_source_pdfs(sec, sc)

    sections_out.append(sec)

# ── Build summaries ──
by_section_summary = []
for sec in sections_out:
    by_section_summary.append(
        {
            "code": sec["section_code"],
            "number": sec["number"],
            "name": sec["name"],
            "total": sec["total"],
            "pct_of_total": sec["pct_of_total"],
            "chapters": sec.get("chapters", {}),
            "source_pdf": sec.get("source_pdf", ""),
        }
    )
by_section_summary.sort(key=lambda s: s["number"])

# Chapter summary across all sections
all_chapters = {}
for sec in sections_out:
    for k, v in sec.get("chapters", {}).items():
        all_chapters[k] = all_chapters.get(k, 0) + v

by_chapter_summary = [
    {
        "chapter": k,
        "label": CHAPTER_LABELS.get(k, k),
        "color": CHAPTER_COLORS.get(k, "#ccc"),
        "total": v,
        "pct_of_total": round(v / TOTAL_ADMINISTRATION * 100, 2),
    }
    for k, v in sorted(all_chapters.items())
]

# ── Master JSON ──
master = {
    "meta": {
        "title": "Pressupost Generalitat Valenciana 2025",
        "year": 2025,
        "language": "ca",
        "total_administration": TOTAL_ADMINISTRATION,
        "total_consolidated": 34202706.82,
        "currency": "EUR",
        "unit": "milers d'euros",
        "last_updated": "2025-05-16",
        "source_url": "https://hisenda.gva.es/auto/presupuestos/2025/index_val.html",
        "source_base": "https://hisenda.gva.es/auto/presupuestos/2025/",
        "source_pdf_base": "https://hisenda.gva.es/auto/presupuestos/2025/pdf/",
    },
    "summaries": {
        "by_section": by_section_summary,
        "by_chapter": by_chapter_summary,
    },
    "chapter_labels": CHAPTER_LABELS,
    "chapter_colors": CHAPTER_COLORS,
    "sections": sections_out,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")


def walk_programs(node):
    if node.get("type") == "program":
        yield node
    for child in node.get("children", []):
        yield from walk_programs(child)


prog_total = sum(sec["total"] for sec in sections_out)
print(f"Total sections: {len(sections_out)}")
print(f"Total programs: {sum(1 for sec in sections_out for _ in walk_programs(sec))}")
print(f"Sum of section totals: {prog_total:,.2f}")
print(f"Expected:            {TOTAL_ADMINISTRATION:,.2f}")
print(f"Match: {'✓' if abs(prog_total - TOTAL_ADMINISTRATION) < 0.01 else '✗'}")
print(f"\nWritten to {OUT}")
