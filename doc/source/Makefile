#
# Generate PyInstaller documentation
#

.PHONY: all doc pdf man html clean cleanall cleanlogs

all:
	@echo "make doc   ===> To generate html and pdf of the documentation and man pages"
	@echo "make html  ===> To generate a html of the documentation"
	@echo "make pdf   ===> To generate a pdf of the documentation"
	@echo "make man   ===> To generate man pages documentation"


doc: html pdf man cleanlogs
	@echo "Documentation generated: Please see ../*.html, ../*.pdf and ../*.1 for files"

manpages := pyinstaller pyi-makespec pyi-build pyi-makeCOMServer

html: ../Manual.html $(foreach manpage,${manpages},../${manpage}.html)
pdf: ../Manual.pdf
man: $(foreach manpage,${manpages},../${manpage}.1)

../%.1: %.rst docutils-man.conf docutils.conf _definitions.txt
	rst2man.py --config=docutils-man.conf $< $@

../%.html: %.rst docutils.conf _definitions.txt
	rst2html --config=docutils.conf $< $@

Manual.tex: Manual.rst _definitions.txt
	tools/rst2newlatex.py --stylesheet-path=stylesheets/latex.tex Manual.rst Manual.tex

../Manual.pdf: srcdir=$(dir $(abspath $<))
../Manual.pdf: Manual.rst _definitions.txt
	cp _definitions.txt ..
	cd ${srcdir}/.. && \
	rst2pdf < ${srcdir}/$< -o ${srcdir}/$@ \
	   --header='###Title### - ###Section###' \
	   --footer='###Page###' \
	   --default-dpi=75 
	rm ../_definitions.txt

_definitions.txt:
	# _definitions.txt is overwritten.
	echo '.. -*- mode: rst ; ispell-local-dictionary: "american" -*-' > $@
	echo '' >> $@  # Empty line.
	# Append other lines.
	echo '.. _PyInstaller: http://www.pyinstaller.org' >> $@
	echo '' >> $@
	echo '.. |Homepage| replace:: http://www.pyinstaller.org' >> $@
	echo '.. |PyInstaller| replace:: `PyInstaller`' >> $@
	# run `pyinstaller.py -v` to get the version
	echo '.. |Version| replace::' `python ../../pyinstaller.py -v` >> $@
	echo '.. |PyInstallerVersion| replace:: PyInstaller |Version|' >> $@
	echo '.. |install_path| replace:: /your/path/to/pyinstaller/' >> $@

clean:
	@echo "make cleanall  ===> To clean everything"
	@echo "make cleanlogs ===> To clean *.log, *.aux, etc. but not the .html or .pdf"


cleanall: cleanlogs
	rm -f ../*.pdf ../*.html ../*.1
	rm _definitions.txt
	@echo "All logs and documentation removed."


cleanlogs:
	rm -f ../*.aux ../*.out ../*.log
	rm -f .log *.log
	@echo "All logs and aux removed."

#
# END OF FILE
#
