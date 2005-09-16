#
# Generate PyInstaller documentation
#

.PHONY: doc pdf

all:
	@echo "make doc   ===> To generate a html and pdf of the documentation"
	@echo "make html  ===> To generate a html of the documentation"
	@echo "make pdf   ===> To generate a pdf of the documentation"


doc: html pdf cleanlogs
	@echo "Documentation generated: Please see ../*.html and ../*.pdf for files"


html: ../Tutorial.html
pdf: ../Tutorial.pdf

../Tutorial.html: Tutorial.rst
	tools/buildrecursive.py --local --strict --title="PyInstaller Tutorial" --outpath=..

Tutorial.tex: Tutorial.rst
	tools/rst2newlatex.py --stylesheet-path=stylesheets/latex.tex Tutorial.rst Tutorial.tex

../Tutorial.pdf: Tutorial.tex
	cd .. ; pdflatex source/Tutorial.tex
	@echo "#############################################################################"
	@echo "# Executing again to fix Table of Content...                                #"
	@echo "#############################################################################"
	cd .. ; pdflatex source/Tutorial.tex

clean:
	@echo "make cleanall  ===> To clean everything"
	@echo "make cleanlogs ===> To clean *.log, *.aux, etc. but not the .html or .pdf"


cleanall: cleanlogs
	rm -f ../*.pdf
	rm -f ../*.html
	@echo "All logs and documentation removed."


cleanlogs:
	rm -f ../*.aux
	rm -f ../*.out
	rm -f .log *.log  ../*.log
	@echo "All logs and aux removed."


#
# END OF FILE
#
