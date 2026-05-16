import json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup, Tag

BASE = Path("hisenda.gva.es/auto/presupuestos/2025")
OUT = Path("step1_hierarchy.json")


# ── G-code mapping from T1_i_lsec_VA.html ──
def extract_gcode_map():
    html = (BASE / "T1_i_lsec_VA.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    gcode_map = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        m = re.search(r"G(\d{4})", href)
        num = re.search(r"(\d+)\s*\.\s*-", text)
        if m and num:
            gcode_map[f"G{m.group(1)}"] = {
                "number": num.group(1),
                "name": re.sub(r"^\d+\s*\.\s*-?\s*", "", text).strip(),
            }
    return gcode_map


GCODE_MAP = extract_gcode_map()
print(f"G-code mapping: {len(GCODE_MAP)} sections")


# ── Section numbers from T2_menu_epp_VA.html (for ordering) ──
def extract_section_order():
    html = (BASE / "T2_menu_epp_VA.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    order = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        m = re.match(r"(\d+)\.\s*-\s*(.+)", text)
        if m:
            order.append(m.group(1))
    return order


SECTION_ORDER = extract_section_order()
print(f"Section order: {len(SECTION_ORDER)} entries")

# ── Helper: extract section number from a section text like "09.- Educació..." ──
SEC_RE = re.compile(r"^(\d+)\.\s*-\s*(.+)$")
PROG_RE = re.compile(r"^(\d{3}[A-Z0-9]\d{2})\.\s*-\s*(.+)$")


# ── Recursive parser ──
def parse_ul(ul: Tag, depth: int = 0, section_number: str = ""):
    nodes = []
    children = [c for c in ul.children if isinstance(c, Tag)]

    i = 0
    while i < len(children):
        child = children[i]
        if child.name != "li":
            i += 1
            continue

        text = child.get_text(strip=True)

        # Skip items with links or empty text
        if child.find("a") or not text:
            j = i + 1
            while j < len(children) and children[j].name == "ul":
                j += 1
            i = j
            continue

        node = {}

        prog_m = PROG_RE.match(text)
        sec_m = SEC_RE.match(text)

        if prog_m:
            node["type"] = "program"
            node["code"] = prog_m.group(1)
            node["name"] = prog_m.group(2).strip()
        elif sec_m:
            node["name"] = sec_m.group(2).strip()
            if depth == 0:
                node["type"] = "section"
                node["number"] = sec_m.group(1)
            elif depth == 1:
                node["type"] = "sa"
            elif depth == 2:
                node["type"] = "dg"
            else:
                node["type"] = f"level{depth}"
        else:
            # Unknown text - skip
            j = i + 1
            while j < len(children) and children[j].name == "ul":
                j += 1
            i = j
            continue

        # Collect ALL consecutive <ul> siblings as children
        child_nodes = []
        j = i + 1
        while j < len(children) and children[j].name == "ul":
            sub = parse_ul(children[j], depth + 1, section_number)
            child_nodes.extend(sub)
            j += 1

        if child_nodes:
            node["children"] = child_nodes
        i = j

        nodes.append(node)

    return nodes


# ── Process section files ──
sections = []
html_files = sorted(BASE.glob("T2_sec??_VA.html"))

for fp in html_files:
    m = re.search(r"T2_sec(\d+)_VA\.html", fp.name)
    if not m:
        continue
    sec_num = m.group(1)
    if sec_num not in SECTION_ORDER:
        print(f"  WARN: section {sec_num} not in menu, skipping")
        continue

    html = fp.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Find the root ul (it's the only one at top level, inside body)
    root_ul = soup.find("ul")
    if not root_ul:
        print(f"  WARN: no ul in {fp.name}")
        continue

    parsed = parse_ul(root_ul, depth=0, section_number=sec_num)

    # Find the section node (first non-skip node at depth 0)
    section_node = None
    for p in parsed:
        if p.get("type") == "section":
            section_node = p
            break

    if not section_node:
        print(f"  WARN: no section node found in {fp.name}")
        continue

    # Attach section metadata
    gcode = None
    for code, info in GCODE_MAP.items():
        if info["number"] == sec_num:
            gcode = code
            break

    section_node["section_code"] = gcode or f"G{sec_num}"
    section_node["source_html"] = fp.name

    # Extract the actual RPC PDF href from the HTML
    rpc_link = soup.find("a", href=lambda h: h and "RPC-" in h)
    section_node["source_pdf"] = rpc_link["href"] if rpc_link else ""

    sections.append(section_node)
    print(f"  {fp.name}: section {sec_num} ({section_node.get('name', '?')})")

# Sort by section number per menu order
sec_by_num = {s["number"]: s for s in sections}
sections_sorted = [sec_by_num[n] for n in SECTION_ORDER if n in sec_by_num]
print(f"\nTotal sections parsed: {len(sections_sorted)}")


def walk_programs(node):
    if node.get("type") == "program":
        yield node
    for child in node.get("children", []):
        yield from walk_programs(child)


prog_names = []
for sec in sections_sorted:
    for p in walk_programs(sec):
        prog_names.append(f"    {p['code']} - {p['name']}")
print(f"Total programs: {len(prog_names)}")
for pn in prog_names:
    print(pn)

# Write output
output = {
    "meta": {
        "generated_by": "step1_parse_html.py",
        "total_sections": len(sections_sorted),
        "total_programs": len(prog_names),
    },
    "sections": sections_sorted,
}
OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nWritten to {OUT}")
