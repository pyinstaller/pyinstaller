#
# Generate PyInstaller documentation
#

.PHONY: doc pdf man

all:
	@echo "make doc   ===> To generate html and pdf of the documentation and man pages"
	@echo "make html  ===> To generate a html of the documentation"
	@echo "make pdf   ===> To generate a pdf of the documentation"
	@echo "make man   ===> To generate man pages documentation"


doc: html pdf man cleanlogs
	@echo "Documentation generated: Please see ../*.html and ../*.pdf for files"


html: ../Manual.html
pdf: ../Manual.pdf
man: ../pyi-configure.1 ../pyi-makespec.1 ../pyi-build.1 ../pyinstaller.1 \
	../pyi-makeCOMServer.1

../%.1: %.rst docutils-man.conf docutils.conf _definitions.txt
	rst2man.py --config=docutils-man.conf $< $@

../Manual.html: Manual.rst docutils.conf _definitions.txt
	rst2html.py --config=docutils.conf $< $@

Manual.tex: Manual.rst _definitions.txt
	tools/rst2newlatex.py --stylesheet-path=stylesheets/latex.tex Manual.rst Manual.tex

../Manual.pdf: srcdir=$(dir $(abspath $<))
../Manual.pdf: Manual.rst _definitions.txt
	cd ${srcdir}/.. && \
	rst2pdf < ${srcdir}/$< -o ${srcdir}/$@ \
	   --header='###Title### - ###Section###' \
	   --footer='###Page###' \
	   --default-dpi=75 

clean:
	@echo "make cleanall  ===> To clean everything"
	@echo "make cleanlogs ===> To clean *.log, *.aux, etc. but not the .html or .pdf"


cleanall: cleanlogs
	rm -f ../*.pdf
	rm -f ../*.html
	rm -f ../*.1
	@echo "All logs and documentation removed."


cleanlogs:
	rm -f ../*.aux
	rm -f ../*.out
	rm -f .log *.log  ../*.log
	@echo "All logs and aux removed."


#
# END OF FILE
#
