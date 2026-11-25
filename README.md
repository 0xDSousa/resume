# Resume

Code-based, ATS-friendly CV driven by a single YAML source (`cv.yaml`) and rendered with [Typst](https://typst.app/).

## Prerequisites

- [Typst](https://typst.app/) (`typst`)
- [uv](https://docs.astral.sh/uv/) (for the `ats_audit.py` check)
- Poppler (`pdftotext`, `pdftoppm`) for ATS text auditing and PNG previews

## Usage

```bash
make all           # Build light, dark, and photo PDF variants + run ATS audit
make test          # Build all PDFs + run 6-extractor ATS pytest suite (149 tests)
make install-hooks # Enable the local git pre-commit hook (.githooks/pre-commit)
make previews      # Build all PDFs, run ATS audit, and generate PNG previews
make watch         # Live-recompile build/Diogo_Sousa_CV.pdf on edit
make clean         # Remove generated build/ outputs
```

### Variants Generated (`build/`)

- `Diogo_Sousa_CV.pdf` — Light mode, no photo (recommended for ATS portals)
- `Diogo_Sousa_CV_photo.pdf` — Light mode with headshot
- `Diogo_Sousa_CV_dark.pdf` — Dark mode, no photo
- `Diogo_Sousa_CV_dark_photo.pdf` — Dark mode with headshot

## Structure

- `cv.yaml` — CV content (single source of truth)
- `template.typ` — Typst layout template (single-column, ligatures & hyphenation disabled for ATS compatibility)
- `assets/photo.jpg` — Optional headshot toggled via `--input photo=/assets/photo.jpg`
- `scripts/ats_audit.py` — Audits generated PDFs with `pdftotext` and `pypdf` (checks page limit, ligatures, icon glyphs, hyphen breaks, clickable links, and text parity across variants)
- `tests/test_ats_extractors.py` — `pytest` suite verifying every PDF variant across 6 distinct PDF extractors (Poppler raw, Poppler layout, `pypdf`, `pdfminer.six`, `PyMuPDF`, `pypdfium2`)
- `.github/workflows/build-cv.yml` — Builds all 4 PDFs on `v*` tag pushes (or manual dispatch), runs the strict ATS audit + 6-extractor test suite, uploads PDFs as workflow artifacts, and publishes a GitHub Release
