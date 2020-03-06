#Modified pyinstaller fork

This is a pyinstaller fork, modified to suit Infection Monkey scanner. 
Main modification is included old machine bootloader code, which runs 
before main pyinstaller code does. 

# Build linux

1. Build libcurl from source with these commands:
```
./configure --disable-maintainer-mode --disable-ftp --disable-ldap --disable-ldaps --disable-rtsp --disable-dict --disable-telnet --disable-tftp --disable-pop3 --disable-imap --disable-smb --disable-gopher --disable-manual --without-polarssl --without-mbedtls --without-cyassl --without-nss --without-axtls --without-libssh2 --without-librtmp --without-ssl --with-gnutls --disable-verbose --disable-smtp --disable-libcurl-option --disable-shared
make
sudo make install
```
2. To build bootloader run
```
python ./waf all
```

# Build windows
1. To build bootloader run
```
python ./waf all
```
