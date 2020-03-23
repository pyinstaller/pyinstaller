#!/bin/bash -i
wget -q https://curl.haxx.se/download/curl-7.69.1.tar.gz
tar -xf curl-7.69.1.tar.gz
rm curl-7.69.1.tar.gz
pushd curl-7.69.1
./configure --disable-maintainer-mode --disable-ftp --disable-ldap --disable-ldaps --disable-rtsp --disable-dict --disable-telnet --disable-tftp --disable-pop3 --disable-imap --disable-smb --disable-gopher --disable-manual --without-polarssl --without-mbedtls --without-cyassl --without-nss --without-axtls --without-libssh2 --without-librtmp --without-ssl --with-gnutls --disable-verbose --disable-smtp --disable-shared --disable-threaded-resolver --disable-libcurl-option --enable-static
# to remove the requirement for clock_gettime we have to do a horrible hack
sed -i '/#define HAVE_CLOCK_GETTIME_MONOTONIC 1/d' lib/curl_config.h
make
make install
popd
pushd bootloader
python ./waf all
popd
rm -rf curl-7.69.1

