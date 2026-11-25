.PHONY: all pdf photo dark dark-photo previews test install-hooks watch audit clean

PHOTO_FILE ?= assets/photo.jpg
FONT ?= Nimbus Sans
PDF := build/Diogo_Sousa_CV.pdf
PDF_PHOTO := build/Diogo_Sousa_CV_photo.pdf
PDF_DARK := build/Diogo_Sousa_CV_dark.pdf
PDF_DARK_PHOTO := build/Diogo_Sousa_CV_dark_photo.pdf

all: pdf photo dark dark-photo audit

pdf:
	mkdir -p build
	typst compile --root . --input font="$(FONT)" template.typ $(PDF)

photo:
	mkdir -p build
	typst compile --root . --input font="$(FONT)" --input photo=/$(PHOTO_FILE) template.typ $(PDF_PHOTO)

dark:
	mkdir -p build
	typst compile --root . --input font="$(FONT)" --input theme=dark template.typ $(PDF_DARK)

dark-photo:
	mkdir -p build
	typst compile --root . --input font="$(FONT)" --input theme=dark --input photo=/$(PHOTO_FILE) template.typ $(PDF_DARK_PHOTO)

audit:
	uv run python scripts/ats_audit.py --strict --max-pages 2

test: all
	uv run pytest -v

install-hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit

previews: all
	mkdir -p build/previews
	rm -f build/previews/*.png
	pdftoppm -png -r 140 $(PDF) build/previews/cv_light
	pdftoppm -png -r 140 $(PDF_PHOTO) build/previews/cv_light_photo
	pdftoppm -png -r 140 $(PDF_DARK) build/previews/cv_dark
	pdftoppm -png -r 140 $(PDF_DARK_PHOTO) build/previews/cv_dark_photo

font-sampler:
	mkdir -p build/fonts
	rm -f build/fonts/*.pdf build/fonts/*.png
	for f in "Nimbus Sans" "Lato" "Ubuntu Sans" "Noto Sans" "Libertinus Serif"; do \
		slug=$$(echo "$$f" | tr '[:upper:] ' '[:lower:]_'); \
		typst compile --root . --input font="$$f" --input photo=/$(PHOTO_FILE) template.typ "build/fonts/cv_$$slug.pdf"; \
		pdftoppm -png -r 140 -f 1 -l 1 "build/fonts/cv_$$slug.pdf" "build/fonts/cv_$$slug"; \
	done

watch:
	mkdir -p build
	typst watch --root . --input font="$(FONT)" template.typ $(PDF)

clean:
	rm -rf build
