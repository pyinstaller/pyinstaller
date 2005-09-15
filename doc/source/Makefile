#
# Generate PyInstaller documentation
#

.PHONY: doc pdf

all: doc

doc: ../Tutorial.html
pdf: ../Tutorial.pdf

../Tutorial.html: Tutorial.rst
	tools/buildrecursive.py --local --strict --title="PyInstaller Tutorial" --outpath=..

Tutorial.tex: Tutorial.rst
	tools/rst2newlatex.py --stylesheet-path=stylesheets/latex.tex Tutorial.rst Tutorial.tex

../Tutorial.pdf: Tutorial.tex
	cd .. ; pdflatex source/Tutorial.tex

clean:
	rm -f ../*.html
	rm -f ../*.pdf
	rm -f ../*.aux
	rm -f ../*.out


#
# END OF FILE
#
