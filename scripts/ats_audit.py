#!/usr/bin/env python3
"""Audit generated CV PDFs for ATS parseability using pdftotext and pypdf."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

LIGATURES = ["\ufb00", "\ufb01", "\ufb02", "\ufb03", "\ufb04", "\ufb05", "\ufb06"]
KEY_TOKENS = [
    "Diogo Sousa",
    "diogo.edgar.sousa@gmail.com",
    "Canonical",
    "Platform.sh",
    "Security Engineering",
    "CISSP",
    "CISA KEV",
    "OWASP",
    "Information Security",
    "Quorum Born IT",
]


def run_pdftotext(pdf: Path, mode: str) -> str:
    res = subprocess.run(
        ["pdftotext", mode, str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


def analyze_pdf(pdf: Path, out_dir: Path, max_pages: int) -> tuple[str, list[str]]:
    reader = PdfReader(str(pdf))
    pypdf_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    raw_text = run_pdftotext(pdf, "-raw")
    layout_text = run_pdftotext(pdf, "-layout")

    stem = pdf.stem
    (out_dir / f"{stem}_raw.txt").write_text(raw_text, encoding="utf-8")
    (out_dir / f"{stem}_layout.txt").write_text(layout_text, encoding="utf-8")

    lig_hits = [c for c in LIGATURES if c in raw_text or c in pypdf_text]
    pua_hits = sorted(set(re.findall(r"[\ue000-\uf8ff]", raw_text + pypdf_text)))
    hyphen_breaks = re.findall(r"[A-Za-z]+-\n[a-z]+", raw_text)
    missing_tokens = [tok for tok in KEY_TOKENS if tok not in raw_text]
    links = []
    for page in reader.pages:
        for annot in page.get("/Annots") or []:
            obj = annot.get_object()
            action = obj.get("/A")
            if action and "/URI" in action:
                links.append(str(action["/URI"]))

    failures = []
    if len(reader.pages) > max_pages:
        failures.append(f"exceeded max pages ({len(reader.pages)} > {max_pages})")
    if lig_hits:
        failures.append(f"ligatures found: {lig_hits}")
    if pua_hits:
        failures.append(f"private-use icon glyphs found: {[hex(ord(c)) for c in pua_hits]}")
    if hyphen_breaks:
        failures.append(f"line-end hyphen breaks found: {hyphen_breaks}")
    if missing_tokens:
        failures.append(f"missing key fields: {missing_tokens}")

    size_kb = pdf.stat().st_size / 1024
    words = len(raw_text.split())

    print(f"\n=== {pdf.name} ===")
    print(f"Pages: {len(reader.pages)} | Size: {size_kb:.1f} KB | Words: {words} | Clickable URIs: {len(links)}")
    print(f"Ligatures: {len(lig_hits)} {'(PASS)' if not lig_hits else lig_hits} | "
          f"Icon/PUA glyphs: {len(pua_hits)} {'(PASS)' if not pua_hits else pua_hits} | "
          f"Hyphen breaks: {len(hyphen_breaks)} {'(PASS)' if not hyphen_breaks else hyphen_breaks[:5]}")
    print(f"Key fields: {'PASS' if not missing_tokens else f'MISSING: {missing_tokens}'}")
    return raw_text, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated CV PDFs for ATS compatibility.")
    parser.add_argument("pdfs", nargs="*", help="Specific PDF paths (defaults to build/*.pdf)")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any ATS or page-limit check fails")
    parser.add_argument("--max-pages", type=int, default=2, help="Maximum allowed pages in strict mode (default: 2)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    build_dir = root / "build"
    audit_dir = build_dir / "ats-audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    pdfs = [Path(p) for p in args.pdfs] if args.pdfs else sorted(build_dir.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in build/", file=sys.stderr)
        return 1

    extracted = {}
    all_failures: list[str] = []
    for pdf in pdfs:
        if pdf.exists():
            text, failures = analyze_pdf(pdf, audit_dir, args.max_pages)
            extracted[pdf.name] = text
            for f in failures:
                all_failures.append(f"{pdf.name}: {f}")

    if len(extracted) >= 2:
        names = list(extracted.keys())
        baseline = extracted[names[0]]
        all_same = all(text == baseline for text in extracted.values())
        print(f"\nText parity across all {len(names)} variants: {'IDENTICAL (PASS)' if all_same else 'DIFFERS'}")
        if not all_same:
            all_failures.append("text parity differs across variants")

    print(f"ATS text dumps saved in: {audit_dir}")

    if args.strict and all_failures:
        print("\nSTRICT AUDIT FAILED:", file=sys.stderr)
        for f in all_failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
