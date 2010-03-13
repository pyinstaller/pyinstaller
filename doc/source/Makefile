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


html: ../Manual.html
pdf: ../Manual.pdf

../Manual.html: Manual.rst
	tools/buildrecursive.py --local --strict --title='PyInstaller Manual' --outpath=..

Manual.tex: Manual.rst
	tools/rst2newlatex.py --stylesheet-path=stylesheets/latex.tex Manual.rst Manual.tex

../Manual.pdf: ../Manual.html
	wkhtmltopdf ../Manual.html ../Manual.pdf

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
