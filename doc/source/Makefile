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

manpages := pyinstaller pyi-makespec pyi-build pyi-make_comserver

html: ../Manual.html $(foreach manpage,${manpages},../${manpage}.html)
pdf: ../Manual.pdf
man: $(foreach manpage,${manpages},../${manpage}.1)

../%.1: %.rst docutils-man.conf docutils.conf _definitions.txt
	rst2man.py --config=docutils-man.conf $< $@

../%.html: %.rst docutils.conf _definitions.txt
	rst2html --config=docutils.conf $< $@

Manual.rst: _pyinstaller-options.tmp
pyinstaller.rst: _pyinstaller-options.tmp
pyi-makespec.rst: _pyi-makespec-options.tmp
pyi-build.rst: _pyi-build-options.tmp
pyi-make_comserver.rst: _pyi-make_comserver-options.tmp

_pyinstaller-options.tmp: ../../pyinstaller.py
	./help2rst $< > $@

_pyi-%-options.tmp: ../../utils/%.py
	./help2rst $< > $@

# rst2pdf need to find some images *and* the include-files in the
# same dircectory, so copy the include-files up there.
../Manual.pdf: srcdir=$(dir $(abspath $<))
../Manual.pdf: Manual.rst _definitions.txt _pyinstaller-options.tmp
	cp _definitions.txt _pyinstaller-options.tmp ..
	cd ${srcdir}/.. && \
	rst2pdf < ${srcdir}/$< \
	   --header='###Title### - ###Section###' \
	   --footer='###Page###' \
	   --default-dpi=75 | \
	gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite \
	   '-sOutputFile=${srcdir}/$@' -c save pop -
	rm ../_definitions.txt ../_pyinstaller-options.tmp

_definitions.txt:
	@echo Overwritung '_definitions.txt'
	@echo '.. -*- mode: rst ; ispell-local-dictionary: "american" -*-' > $@
	@echo '' >> $@  # Empty line.
	@# Append other lines.
	@echo '.. _PyInstaller: http://www.pyinstaller.org' >> $@
	@echo '' >> $@
	@echo '.. |Homepage| replace:: http://www.pyinstaller.org' >> $@
	@echo '.. |PyInstaller| replace:: `PyInstaller`' >> $@
	@# run `pyinstaller.py -v` to get the version
	@echo '.. |Version| replace::' `python ../../pyinstaller.py -v` >> $@
	@echo '.. |PyInstallerVersion| replace:: PyInstaller |Version|' >> $@
	@echo '.. |install_path| replace:: /OBSOLETE-REMOVE/' >> $@
	@# folder name of package after download and unzip
	@echo '.. |unzipped_download| replace:: ``pyinstaller``' >> $@
	@# how we punctuate boot loader as a proper noun "the bootloader"
	@echo '.. |bootloader| replace:: bootloader' >> $@

clean:
	@echo "make cleanall  ===> To clean everything"
	@echo "make cleanlogs ===> To clean *.log, *.aux, etc. but not the .html or .pdf"


cleanall: cleanlogs
	@# Checkout last commited version to avoid '-mod' postfix in version
	git checkout --quiet --force -- ../*.pdf ../*.html
	rm -f ../*.1
	rm -f _definitions.txt _*-options.tmp
	@echo "All generated documentation removed."


cleanlogs:
	rm -f ../*.aux ../*.out ../*.log
	rm -f .log *.log
	@echo "All logs and aux removed."

#
# END OF FILE
#
