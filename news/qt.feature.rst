Improved support for Qt5-based applications.
By emulating much of the Qt deployment tools' behavior
most PyQt5 variants are supported.
However, Anaconda's PyQt5 packages are not supported
because its ``QlibraryInfo`` implementation reports incorrect values.
CI tests currently run on PyQt5 5.11.2.
