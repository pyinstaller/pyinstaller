# email.message imports the old-style naming of two modules:
# email.Iterators and email.Generator. Since those modules
# don't exist anymore and there are import trick to map them
# to the real modules (lowercase), we need to specify them
# as hidden imports to make PyInstaller package them.
hiddenimports = [ "email.iterators", "email.generator" ]
