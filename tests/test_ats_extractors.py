"""Multi-engine ATS PDF extraction test suite.

Verifies every generated CV PDF variant against 6 distinct PDF text extractors:
  1. poppler_raw    — Poppler (pdftotext -raw, C++ content-stream order)
  2. poppler_layout — Poppler (pdftotext -layout, C++ spatial layout)
  3. pypdf          — Pure-Python PDF stream parser (common in LLM/Python pipelines)
  4. pdfminer       — pdfminer.six Python layout analysis engine
  5. pymupdf        — MuPDF C engine (fitz)
  6. pypdfium2      — Google Chrome PDFium C++ engine
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pymupdf
import pypdfium2 as pdfium
import pytest
import yaml
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
CV_YAML = ROOT / "cv.yaml"

PDF_VARIANTS = [
    "Diogo_Sousa_CV.pdf",
    "Diogo_Sousa_CV_photo.pdf",
    "Diogo_Sousa_CV_dark.pdf",
    "Diogo_Sousa_CV_dark_photo.pdf",
]

LIGATURES = ["\ufb00", "\ufb01", "\ufb02", "\ufb03", "\ufb04", "\ufb05", "\ufb06"]
MAX_PAGES = 2


# ---------------------------------------------------------------------------
# 6 Distinct PDF Extraction Engines
# ---------------------------------------------------------------------------

def extract_poppler_raw(pdf: Path) -> str:
    res = subprocess.run(["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True, check=True)
    return res.stdout


def extract_poppler_layout(pdf: Path) -> str:
    res = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True)
    return res.stdout


def extract_pypdf(pdf: Path) -> str:
    reader = PdfReader(str(pdf))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_pdfminer(pdf: Path) -> str:
    return pdfminer_extract_text(str(pdf)) or ""


def extract_pymupdf(pdf: Path) -> str:
    with pymupdf.open(str(pdf)) as doc:
        return "\n".join(page.get_text("text") for page in doc)


def extract_pypdfium2(pdf: Path) -> str:
    doc = pdfium.PdfDocument(str(pdf))
    try:
        pages = []
        for i in range(len(doc)):
            page = doc[i]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_range())
            textpage.close()
            page.close()
        return "\n".join(pages)
    finally:
        doc.close()


EXTRACTORS = {
    "poppler_raw": extract_poppler_raw,
    "poppler_layout": extract_poppler_layout,
    "pypdf": extract_pypdf,
    "pdfminer": extract_pdfminer,
    "pymupdf": extract_pymupdf,
    "pypdfium2": extract_pypdfium2,
}


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_md(text: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", str(text))
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    return s


@pytest.fixture(scope="session")
def cv_data() -> dict:
    return yaml.safe_load(CV_YAML.read_text(encoding="utf-8"))["cv"]


@pytest.fixture(scope="session")
def extracted_matrix() -> dict[tuple[str, str], str]:
    """Extract every PDF variant with every engine once per test session."""
    matrix: dict[tuple[str, str], str] = {}
    for pdf_name in PDF_VARIANTS:
        pdf_path = BUILD_DIR / pdf_name
        assert pdf_path.exists(), f"Missing built PDF: {pdf_path}. Run `make all` first."
        for engine_name, fn in EXTRACTORS.items():
            matrix[(pdf_name, engine_name)] = fn(pdf_path)
    return matrix


# ---------------------------------------------------------------------------
# Tests: PDF Structure & Hyperlinks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
def test_page_count_within_limit(pdf_name: str) -> None:
    pdf_path = BUILD_DIR / pdf_name
    reader = PdfReader(str(pdf_path))
    assert 1 <= len(reader.pages) <= MAX_PAGES, f"{pdf_name} has {len(reader.pages)} pages (max {MAX_PAGES})"


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
def test_all_yaml_links_present_as_clickable_uris(pdf_name: str, cv_data: dict) -> None:
    pdf_path = BUILD_DIR / pdf_name
    reader = PdfReader(str(pdf_path))
    found_uris: set[str] = set()
    for page in reader.pages:
        for annot in page.get("/Annots") or []:
            action = annot.get_object().get("/A")
            if action and "/URI" in action:
                found_uris.add(str(action["/URI"]))

    expected_uris: set[str] = set()
    if cv_data.get("email"):
        expected_uris.add(f"mailto:{cv_data['email']}")
    for sn in cv_data.get("social_networks") or []:
        net = sn["network"].lower()
        user = sn["username"]
        if net == "linkedin":
            expected_uris.add(f"https://linkedin.com/in/{user}")
        elif net == "github":
            expected_uris.add(f"https://github.com/{user}")

    raw_yaml = CV_YAML.read_text(encoding="utf-8")
    for match in re.finditer(r"\[[^\]]+\]\((https?://[^)]+)\)", raw_yaml):
        expected_uris.add(match.group(1))

    missing = expected_uris - found_uris
    assert not missing, f"{pdf_name} missing clickable URIs: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Tests: 6-Extractor Matrix Checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_no_ats_typography_hazards(pdf_name: str, engine_name: str, extracted_matrix: dict) -> None:
    text = extracted_matrix[(pdf_name, engine_name)]

    lig_hits = [c for c in LIGATURES if c in text]
    assert not lig_hits, f"{pdf_name} [{engine_name}] contains ligature glyphs: {[hex(ord(c)) for c in lig_hits]}"

    pua_hits = sorted(set(re.findall(r"[\ue000-\uf8ff]", text)))
    assert not pua_hits, f"{pdf_name} [{engine_name}] contains private-use icon glyphs: {[hex(ord(c)) for c in pua_hits]}"

    hyphen_breaks = re.findall(r"[A-Za-z]+-\r?\n[a-z]+", text)
    assert not hyphen_breaks, f"{pdf_name} [{engine_name}] contains line-end hyphen breaks: {hyphen_breaks}"


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_all_critical_cv_fields_extracted(
    pdf_name: str, engine_name: str, cv_data: dict, extracted_matrix: dict
) -> None:
    flat = normalize_ws(extracted_matrix[(pdf_name, engine_name)])

    required_tokens = [
        cv_data["name"],
        cv_data["headline"],
        cv_data["location"],
        cv_data["email"],
    ]
    for sn in cv_data.get("social_networks") or []:
        required_tokens.append(sn["username"])

    for sec_key, entries in cv_data["sections"].items():
        required_tokens.append(sec_key.replace("_", " ").upper())
        for entry in entries:
            if isinstance(entry, dict):
                if "company" in entry:
                    required_tokens.append(entry["company"])
                    required_tokens.append(entry["position"])
                if "institution" in entry:
                    required_tokens.append(entry["institution"])
                    if entry.get("degree"):
                        required_tokens.append(f"{entry['degree']} in {entry['area']}")
                if "label" in entry:
                    required_tokens.append(entry["label"])
                if "name" in entry:
                    required_tokens.append(strip_md(entry["name"]))

    # Key quantitative/domain tokens from CV body
    required_tokens.extend(["CISSP", "97%", "100+ CVEs", "315", "HIPAA", "94%", "MCP", "OWASP"])

    missing = [tok for tok in required_tokens if tok not in flat]
    assert not missing, f"{pdf_name} [{engine_name}] missing extracted tokens: {missing}"


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_logical_reading_order_preserved(
    pdf_name: str, engine_name: str, cv_data: dict, extracted_matrix: dict
) -> None:
    """Ensure no extractor scrambles sections or chronological entries."""
    flat = normalize_ws(extracted_matrix[(pdf_name, engine_name)])

    ordered_milestones = [
        cv_data["name"],
        cv_data["email"],
        "SUMMARY",
        "SKILLS",
        "EXPERIENCE",
        "Freelance",
        "Canonical",
        "Platform.sh",
        "Manager, Security Engineering & Operations",
        "Security Engineer",
        "Quorum Born IT",
        "COMMUNITY AND SPEAKING",
        "OWASP Lisboa",
        "Selected Public Talks",
        "CERTIFICATIONS",
        "CISSP",
        "EDUCATION",
        "MSc in Information Security",
        "BSc in Informatics Engineering",
        "BSc in Psychology",
    ]

    cursor = -1
    for milestone in ordered_milestones:
        idx = flat.find(milestone, cursor + 1)
        assert idx != -1, (
            f"{pdf_name} [{engine_name}] out-of-order or missing milestone '{milestone}' "
            f"after index {cursor}"
        )
        cursor = idx


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
def test_word_count_consistent_across_all_extractors(pdf_name: str, extracted_matrix: dict) -> None:
    """Catch engines that drop content or merge adjacent words without spaces."""
    counts = {
        engine: len(normalize_ws(extracted_matrix[(pdf_name, engine)]).split())
        for engine in EXTRACTORS
    }
    baseline = counts["poppler_raw"]
    assert baseline >= 500, f"Suspiciously low baseline word count: {baseline}"
    for engine, count in counts.items():
        diff_ratio = abs(count - baseline) / baseline
        assert diff_ratio <= 0.10, (
            f"{pdf_name} word count drift in {engine}: {count} vs poppler_raw {baseline} ({counts})"
        )


@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_all_variants_have_identical_extracted_text(engine_name: str, extracted_matrix: dict) -> None:
    """Light, dark, and photo toggles must never alter extracted text in any engine."""
    baseline_pdf = PDF_VARIANTS[0]
    baseline_text = normalize_ws(extracted_matrix[(baseline_pdf, engine_name)])
    for pdf_name in PDF_VARIANTS[1:]:
        candidate = normalize_ws(extracted_matrix[(pdf_name, engine_name)])
        assert candidate == baseline_text, (
            f"[{engine_name}] extracted text differs between {baseline_pdf} and {pdf_name}"
        )


# ---------------------------------------------------------------------------
# Regression Guards (Prevent Re-introducing Caught ATS Bugs)
# ---------------------------------------------------------------------------

def _collect_struct_tags(obj: object, seen: set[int], tags: set[str]) -> None:
    if hasattr(obj, "get_object"):
        obj = obj.get_object()
    oid = id(obj)
    if oid in seen:
        return
    seen.add(oid)
    if isinstance(obj, dict):
        if "/S" in obj:
            tags.add(str(obj["/S"]))
        if "/K" in obj:
            _collect_struct_tags(obj["/K"], seen, tags)
    elif isinstance(obj, list):
        for item in obj:
            _collect_struct_tags(item, seen, tags)


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
def test_pdf_has_semantic_heading_tags(pdf_name: str) -> None:
    """Ensure Tagged PDF structure contains real /H1 and /H2 headings for PDF/UA & AI parsers."""
    reader = PdfReader(str(BUILD_DIR / pdf_name))
    root = reader.trailer["/Root"].get_object()
    assert "/StructTreeRoot" in root, f"{pdf_name} is missing /StructTreeRoot (not a Tagged PDF)"
    tags: set[str] = set()
    _collect_struct_tags(root["/StructTreeRoot"], set(), tags)
    assert "/H1" in tags, f"{pdf_name} missing semantic /H1 tag (found: {sorted(tags)})"
    assert "/H2" in tags, f"{pdf_name} missing semantic /H2 tags (found: {sorted(tags)})"


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_section_boundaries_prevent_column_leak(
    pdf_name: str, engine_name: str, cv_data: dict, extracted_matrix: dict
) -> None:
    """Catch spatial column clustering bugs (like pdfminer moving Skills values under Experience)."""
    flat = normalize_ws(extracted_matrix[(pdf_name, engine_name)])
    section_titles = [k.replace("_", " ").upper() for k in cv_data["sections"].keys()]

    # Locate every section boundary in order
    positions: dict[str, int] = {}
    cursor = 0
    for title in section_titles:
        idx = flat.find(title, cursor)
        assert idx != -1, f"{pdf_name} [{engine_name}] missing section '{title}'"
        positions[title] = idx
        cursor = idx + len(title)

    # Verify every skill row's label AND first detail token stay strictly inside SKILLS
    if "skills" in cv_data["sections"]:
        skills_start = positions["SKILLS"]
        next_sec = section_titles[section_titles.index("SKILLS") + 1]
        skills_slice = flat[skills_start : positions[next_sec]]
        for row in cv_data["sections"]["skills"]:
            assert row["label"] in skills_slice, (
                f"{pdf_name} [{engine_name}] skill label '{row['label']}' leaked outside SKILLS"
            )
            first_skill = row["details"].split(",")[0].strip()
            assert first_skill in skills_slice, (
                f"{pdf_name} [{engine_name}] skill detail '{first_skill}' leaked outside SKILLS "
                f"(spatial column bug!)"
            )


@pytest.mark.parametrize("pdf_name", PDF_VARIANTS)
@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_plain_text_profile_urls_discoverable(
    pdf_name: str, engine_name: str, cv_data: dict, extracted_matrix: dict
) -> None:
    """Annotation-blind ATS regexes must see full linkedin.com/in/... and github.com/... in plain text."""
    flat = normalize_ws(extracted_matrix[(pdf_name, engine_name)])
    for sn in cv_data.get("social_networks") or []:
        net = sn["network"].lower()
        user = sn["username"]
        if net == "linkedin":
            assert f"linkedin.com/in/{user}" in flat, f"{pdf_name} [{engine_name}] missing plain-text LinkedIn URL"
        elif net == "github":
            assert f"github.com/{user}" in flat, f"{pdf_name} [{engine_name}] missing plain-text GitHub URL"


def test_no_em_dashes_anywhere(extracted_matrix: dict) -> None:
    """Keep prose natural and free of em dashes in both source YAML and extracted PDFs."""
    assert "\u2014" not in CV_YAML.read_text(encoding="utf-8"), "Found em dash in cv.yaml"
    for (pdf_name, engine_name), text in extracted_matrix.items():
        assert "\u2014" not in text, f"Found em dash in {pdf_name} [{engine_name}]"


@pytest.mark.parametrize("engine_name", list(EXTRACTORS.keys()))
def test_key_acronyms_expanded(engine_name: str, extracted_matrix: dict) -> None:
    """Ensure high-value acronyms are spelled out at least once for ATS keyword matching."""
    flat = normalize_ws(extracted_matrix[(PDF_VARIANTS[0], engine_name)])
    for phrase in [
        "Model Context Protocol",
        "CVE Numbering Authority",
        "Certified Information Systems Security Professional",
    ]:
        assert phrase in flat, f"[{engine_name}] missing spelled-out acronym expansion: '{phrase}'"
