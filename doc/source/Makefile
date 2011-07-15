#
# Generate PyInstaller documentation
#

.PHONY: all doc pdf html clean cleanall cleanlogs

all:
	@echo "make doc   ===> To generate a html and pdf of the documentation"
	@echo "make html  ===> To generate a html of the documentation"
	@echo "make pdf   ===> To generate a pdf of the documentation"

doc: html pdf cleanlogs
	@echo "Documentation generated: Please see ../*.html and ../*.pdf for files"

html: ../Manual.html
pdf: ../Manual.pdf

../Manual.html: Manual.rst docutils.conf _definitions.txt
	rst2html --config=docutils.conf $< $@

../Manual.pdf: srcdir=$(dir $(abspath $<))
../Manual.pdf: Manual.rst _definitions.txt
	cp _definitions.txt ..
	cd ${srcdir}/.. && \
	rst2pdf < ${srcdir}/$< -o ${srcdir}/$@ \
	   --header='###Title### - ###Section###' \
	   --footer='###Page###' \
	   --default-dpi=75 
	rm ../_definitions.txt

clean:
	@echo "make cleanall  ===> To clean everything"
	@echo "make cleanlogs ===> To clean *.log, *.aux, etc. but not the .html or .pdf"

cleanall: cleanlogs
	rm -f ../*.pdf ../*.html
	@echo "All logs and documentation removed."

cleanlogs:
	rm -f ../*.aux ../*.out ../*.log
	rm -f .log *.log
	@echo "All logs and aux removed."

#
# END OF FILE
#
