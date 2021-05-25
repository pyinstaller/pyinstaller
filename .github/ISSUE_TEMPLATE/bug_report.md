---
name: Bug report
about: Report a bug encountered while freezing you program or running your frozen program
title: ''
labels: triage
assignees: ''
---

<!--
Welcome to the PyInstaller issue tracker! Before creating an issue, please heed the following:

1. This tracker should only be used to report bugs and request features / enhancements to PyInstaller
    - For questions and general support, use the mailing list, see
	  <http://www.pyinstaller.org/support.html#mailing-list>
2. Use the search function before creating a new issue. Duplicates will be closed and directed to
   the original discussion.
3. When making a bug report, make sure you provide all required information. The easier it is for
   maintainers to reproduce, the faster it'll be fixed.
-->

<!-- +++ ONLY TEXT +++ DO NOT POST IMAGES +++ -->

## Description of the issue

### Context information (for bug reports)

* Output of `pyinstaller --version`: ```(paste here)```
* Version of Python: <!-- e.g. 3.7 -->
* Platform: <!-- e.g GNU/Linux (distribution), Windows (language settings), OS X, FreeBSD -->
* How you installed Python: <!-- e.g. python.org/downloads, conda, brew, pyenv, apt, Windows store -->
* Did you also try this on another platform? Does it work there?


* try the latest development version, using the following command:

```shell
pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip
```

* follow *all* the instructions in our "If Things Go Wrong" Guide
  (https://github.com/pyinstaller/pyinstaller/wiki/If-Things-Go-Wrong) and

### Make sure [everything is packaged correctly](https://github.com/pyinstaller/pyinstaller/wiki/How-to-Report-Bugs#make-sure-everything-is-packaged-correctly)

  * [ ] start with clean installation
  * [ ] use the latest development version
  * [ ] Run your frozen program **from a command window (shell)** — instead of double-clicking on it
  * [ ] Package your program in **--onedir mode**
  * [ ] Package **without UPX**, say: use the option `--noupx` or set `upx=False` in your .spec-file
  * [ ] Repackage you application in **verbose/debug mode**. For this, pass the option `--debug` to `pyi-makespec` or `pyinstaller` or use `EXE(..., debug=1, ...)` in your .spec file.


### A minimal example program which shows the error

```
(paste text here)
“Minimal“ means: remove everything from your code which is not relevant for this bug,
esp. don't use external programs, remote requests, etc.
A very good example is https://gist.github.com/ronen/024cdae9ff2d50488438. This one helped
us reproducing and fixing a quite complex problem within approx 1 hour.
```

### Stacktrace / full error message


```
(paste text here)
```

Please also see <https://github.com/pyinstaller/pyinstaller/wiki/How-to-Report-Bugs>
for more about what would use to solve the issue.
