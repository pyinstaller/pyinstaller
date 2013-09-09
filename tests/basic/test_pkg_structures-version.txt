# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(96, 12, 19, 1), 
    prodvers=(4, 1, 2, 1),
    # Contains a bitmask that specifies the valid bits 'flags'
    mask=0x3f, 
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904b0', 
        [StringStruct(u'CompanyName', u'Fuddy Duddies, Inc. 8 Flossie Dr. Arlington, VA 00001'), 
        StringStruct(u'ProductName', u'SILLINESS'), 
        StringStruct(u'ProductVersion', u'2, 0, 3, 0'),
        StringStruct(u'InternalName', u'SILLINESS'), 
        StringStruct(u'OriginalFilename', u'silliness.exe'), 
        StringStruct(u'FileVersion', u'96, 12, 19, 1'), 
        StringStruct(u'FileDescription', u'Silly stuff'), 
        StringStruct(u'LegalCopyright', u'Copyright 2001 Fuddy Duddies, Inc.'), 
        StringStruct(u'LegalTrademarks', u'SILLINESS is a registered trademark of Fuddy Duddies, Inc.'),])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
