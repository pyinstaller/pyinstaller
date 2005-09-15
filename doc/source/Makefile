#
# Generate PyInstaller documentation
#

.PHONY: doc pdf

all:
	@echo "#############################################################################"
	@echo "# make doc   ===> To generate a html and pdf of the documentation           #"
	@echo "# make html  ===> To generate a html of the documentation                   #"
	@echo "# make pdf   ===> To generate a pdf of the documentation                    #"
	@echo "#############################################################################"


doc: html pdf cleanlogs
	@echo "#############################################################################"
	@echo "# Documentation generated: Please see ../*.html and ../*.pdf for files      #"
	@echo "#############################################################################"


html: ../Tutorial.html
pdf: ../Tutorial.pdf

../Tutorial.html: Tutorial.rst
	@tools/buildrecursive.py --local --strict --title="PyInstaller Tutorial" --outpath=..

Tutorial.tex: Tutorial.rst
	@tools/rst2newlatex.py --stylesheet-path=stylesheets/latex.tex Tutorial.rst Tutorial.tex

../Tutorial.pdf: Tutorial.tex
	@cd .. ; pdflatex source/Tutorial.tex
	@echo "#############################################################################"
	@echo "# Executing again to fix Table of Content...                                #"
	@echo "#############################################################################"
	@cd .. ; pdflatex source/Tutorial.tex

clean:

	@echo "#############################################################################"
	@echo "# make cleanall  ===> To clean everything                                   #"
	@echo "# make cleanlogs ===> To clean *.log, *.aux, etc. but not the .html or .pdf #"
	@echo "#############################################################################"


cleanall: cleanlogs
	@rm -f ../*.pdf
	@rm -f ../*.html
	@echo "#############################################################################"
	@echo "# All logs and documentation removed.                                       #"
	@echo "#############################################################################"


cleanlogs:
	@rm -f ../*.aux
	@rm -f ../*.out
	@rm -f .log *.log  ../*.log
	@echo "#############################################################################"
	@echo "# All logs and aux removed.                                                 #"
	@echo "#############################################################################"


#
# END OF FILE
#
