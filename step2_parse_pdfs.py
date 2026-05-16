import json, re, subprocess, sys
from pathlib import Path

BASE = Path("hisenda.gva.es/auto/presupuestos/2025")
PDF_DIR = BASE / "pdf"
OUT = Path("step2_financials.json")

NUM_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*(?:,\d{2})?$")
PROG_RE = re.compile(r"^\d{3}[A-Z0-9]\d{2}$")

CHAPTER_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
# Column mapping: the 13 parsed numbers map to:
# [0]=Cap1 [1]=Cap2 [2]=Cap3 [3]=Cap4 [4]=Cap5
# [5]=subtot.corrents (skip)
# [6]=Cap6 [7]=Cap7
# [8]=subtot.capital (skip)
# [9]=Cap8 [10]=Cap9
# [11]=subtot.financer (skip)
# [12]=Total General
NUM_TO_CHAPTER = {
    0: "1",
    1: "2",
    2: "3",
    3: "4",
    4: "5",
    6: "6",
    7: "7",
    9: "8",
    10: "9",
}


def parse_catalan_number(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def is_number(s: str) -> bool:
    if not NUM_RE.match(s):
        return False
    # Require at least one thousands separator, decimal comma, or 4+ digits
    # to avoid matching lone digits in program names like "Ciutat Administrativa 9"
    return "." in s or "," in s or len(s) > 3


def extract_numbers(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Split tokens into (non_numbers, numbers) by detecting Catalan numbers from the right."""
    num_idx = len(tokens)
    for i in range(len(tokens) - 1, -1, -1):
        if is_number(tokens[i]):
            num_idx = i
        else:
            break
    return tokens[:num_idx], tokens[num_idx:]


def is_header_or_footer(line: str) -> bool:
    upper = line.strip().upper()
    if not upper:
        return True
    if any(
        kw in upper
        for kw in [
            "(EN MILERS D'EUROS)",
            "PRESSUPOST DE LA GENERALITAT",
            "SECCIÓ:",
            "SUBPROGRAMA",
            "GASTOS DE",
            "COMPRA DE",
            "GASTOS",
            "TRANSFERÈNCIES",
            "FONS DE",
            "OPERACIONS",
            "INVERSIONS",
            "ACTIUS",
            "PASSIUS",
            "CAPÍTOL I",
            "CAPÍTOL II",
            "CAPÍTOL III",
            "CAPÍTOL IV",
            "CAPÍTOL V",
            "CAPÍTOL VI",
            "CAPÍTOL VII",
            "CAPÍTOL VIII",
            "CAPÍTOL IX",
            "TOTAL OPERACIONS",
            "TOTAL GASTOS",
            "DE FUNC.",
        ]
    ):
        return True
    return False


def extract_section_code(text: str) -> str | None:
    m = re.search(r"SECCIÓ:\s*(G\d{4})", text)
    return m.group(1) if m else None


def parse_rpc_pdf(pdf_path: Path) -> dict | None:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR: pdftotext failed on {pdf_path.name}")
        return None

    lines = result.stdout.split("\n")

    # Extract section code
    section_code = None
    for line in lines:
        sc = extract_section_code(line)
        if sc:
            section_code = sc
            break

    if not section_code:
        print(f"  WARN: no section code found in {pdf_path.name}")
        return None

    programs = []
    total_numbers = None
    total_name_parts = []

    current_code = None
    current_name_parts = []
    current_numbers = None

    for line in lines:
        stripped = line.strip()

        # Skip empty and header/footer lines
        if not stripped or is_header_or_footer(stripped):
            # Check if this line has the section code for continuation line numbers
            if "TOTAL GENERAL" in stripped.upper():
                total_name_parts = ["TOTAL GENERAL"]
            continue

        # Check for TOTAL GENERAL
        if stripped.upper().startswith("TOTAL GENERAL"):
            # Flush current program if any
            if current_code:
                programs.append(
                    {
                        "code": current_code,
                        "name": " ".join(current_name_parts),
                        "numbers": current_numbers,
                    }
                )
                current_code = None
                current_name_parts = []
                current_numbers = None

            tokens = stripped.split()
            # "TOTAL GENERAL" ... numbers
            total_name_parts = ["TOTAL GENERAL"]
            nontokens, nums = extract_numbers(tokens)
            if len(nums) >= 13:
                total_numbers = nums[:13]
            continue

        # Check if line starts with program code
        tokens = stripped.split()
        first_token = tokens[0]

        if PROG_RE.match(first_token):
            # Flush previous program
            if current_code:
                programs.append(
                    {
                        "code": current_code,
                        "name": " ".join(current_name_parts),
                        "numbers": current_numbers,
                    }
                )

            current_code = first_token
            remaining = tokens[1:]
            name_tokens, nums = extract_numbers(remaining)
            current_name_parts = name_tokens
            current_numbers = nums if len(nums) >= 13 else None

        else:
            # Continuation line
            if current_code:
                # Check if this line has numbers
                _, nums = extract_numbers(tokens)
                if len(nums) >= 13:
                    # This line has numbers (unusual but possible)
                    name_tokens, nums = extract_numbers(tokens)
                    current_name_parts.extend(name_tokens)
                    current_numbers = nums[:13]
                else:
                    # Just name continuation
                    current_name_parts.append(stripped)

    # Flush last program
    if current_code:
        programs.append(
            {
                "code": current_code,
                "name": " ".join(current_name_parts),
                "numbers": current_numbers,
            }
        )

    # Build output
    output = {
        "section_code": section_code,
        "pdf": pdf_path.name,
        "programs": [],
        "total_general": None,
    }

    for p in programs:
        if not p["numbers"]:
            print(
                f"  WARN: {section_code} {p['code']} {p['name'][:40]}... has no numbers"
            )
            continue

        nums = p["numbers"]
        if len(nums) < 13:
            print(
                f"  WARN: {section_code} {p['code']} expected 13 numbers, got {len(nums)}: {nums}"
            )
            continue

        chapters = {}
        for col, key in NUM_TO_CHAPTER.items():
            val = parse_catalan_number(nums[col])
            if val != 0:
                chapters[key] = val

        total_val = parse_catalan_number(nums[12])

        output["programs"].append(
            {
                "code": p["code"],
                "name": p["name"],
                "chapters": chapters,
                "total": total_val,
            }
        )

    if total_numbers and len(total_numbers) >= 13:
        output["total_general"] = {
            "total": parse_catalan_number(total_numbers[12]),
            "chapters": {
                key: parse_catalan_number(total_numbers[col])
                for col, key in NUM_TO_CHAPTER.items()
            },
        }

    return output


# ── Main ──
pdf_files = sorted(PDF_DIR.glob("RPC-25-10-A-*-G*xxxx-xxxx-xxxxxx-VA.pdf"))
print(f"Found {len(pdf_files)} RPC PDFs")

sections_data = {}

for fp in pdf_files:
    print(f"  Processing {fp.name}...")
    data = parse_rpc_pdf(fp)
    if data:
        sc = data["section_code"]
        sections_data[sc] = data
        n = len(data["programs"])
        tg = data["total_general"]
        tg_str = f", total={tg['total']:.2f}" if tg else ", no total"
        print(f"    {sc}: {n} programs{tg_str}")

# Write output
output = {
    "meta": {
        "generated_by": "step2_parse_pdfs.py",
        "total_sections": len(sections_data),
        "total_programs": sum(len(s["programs"]) for s in sections_data.values()),
    },
    "sections": sections_data,
}

OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nWritten to {OUT}")

# Validate totals
print("\nValidation:")
total_all = 0
for sc, data in sorted(sections_data.items()):
    prog_sum = sum(p["total"] for p in data["programs"])
    tg = data["total_general"]
    tg_total = tg["total"] if tg else 0
    diff = abs(prog_sum - tg_total)
    status = "✓" if diff < 1 else f"✗ diff={diff:.2f}"
    print(f"  {sc}: sum={prog_sum:,.2f}, total={tg_total:,.2f} {status}")
    total_all += prog_sum

print(f"\n  Grand total (all sections): {total_all:,.2f}")
