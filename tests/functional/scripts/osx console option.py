import sys

if sys.stdin.isatty():
    f = open("itsaconsole.txt", "w")
    f.write("true")
    f.close()

