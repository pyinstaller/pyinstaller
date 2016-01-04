#
# Generate PyInstaller documentation
#

.PHONY: all doc pdf man html clean cleanall cleanlogs

all:
	@echo "make doc   ===> To generate html, pdf and man pages"
	@echo "make html  ===> To generate a html of the documentation"
	@echo "make pdf   ===> To generate a pdf of the documentation"
	@echo "make man   ===> To generate man pages documentation"
	@echo "make DO_RELEASE=1 ... ===> Generate documentation for release"
	@echo "                           (suppress git revision in version)"


doc: cleanlogs html pdf man cleanlogs
	@echo "Documentation generated: Please see ../*.html, ../*.pdf and ../*.1 for files"

manpages := pyinstaller pyi-makespec

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

_pyinstaller-options.tmp: ../../pyinstaller.py
	./help2rst $< > $@

_pyi-makespec-options.tmp: ../../makespec.py
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

define ERR_REPO_MODIFIED


*** Error: Must build documentation from an unmodified repository.
*
* You may want to run 'git checkout ..' (mind your changes in this directory!)
* Or run 'make FORCE_MODIFIED=1 ...'
*

endef
export ERR_REPO_MODIFIED

_definitions.txt:
	@echo Writting '_definitions.txt'
	@echo '.. -*- mode: rst ; ispell-local-dictionary: "american" -*-' > $@
	@echo '' >> $@  # Empty line.
	@# Append other lines.
	@echo '.. _PyInstaller: http://www.pyinstaller.org' >> $@
	@echo '' >> $@
	@echo '.. |Homepage| replace:: http://www.pyinstaller.org' >> $@
	@echo '.. |PyInstaller| replace:: `PyInstaller`' >> $@
	@# run `pyinstaller.py -v` to get the version
	@echo -n '.. |Version| replace:: ' >> $@
ifeq "${DO_RELEASE}" ""
	@python ../../pyinstaller.py -v >> $@ 2>&1
else
	@# When doing a release, pass 'sdist' to strip the git revision.
	@python ../../pyinstaller.py -v sdist >> $@ 2>&1
endif
	@echo '.. |PyInstallerVersion| replace:: PyInstaller |Version|' >> $@
	@# folder name of package after download and unzip
	@echo '.. |unzipped_download| replace:: ``pyinstaller``' >> $@
	@# how we punctuate boot loader as a proper noun "the bootloader"
	@echo '.. |bootloader| replace:: bootloader' >> $@
	@# Check if the repository is unmodified
ifeq "${FORCE_MODIFIED}" ""
	@grep -E '\|Version\|.*replace::.*\.mod' $@ && echo "$$ERR_REPO_MODIFIED" && exit 10 || echo
endif


clean:
	@echo "make cleanall  ===> To clean everything"
	@echo "make cleanlogs ===> To clean _definitions.txt, *.log, *.aux, etc. but not the .html or .pdf"


cleanall: cleanlogs
	@# Checkout last commited version to avoid '-mod' postfix in version
	git checkout --quiet --force -- ../*.pdf ../*.html
	rm -f ../*.1
	rm -f _*-options.tmp
	@echo "All generated documentation removed."


cleanlogs:
	rm -f ../*.aux ../*.out ../*.log
	rm -f .log *.log _py*-options.tmp
	rm -f _definitions.txt
	@echo "All logs and aux removed."

#
# END OF FILE
#
