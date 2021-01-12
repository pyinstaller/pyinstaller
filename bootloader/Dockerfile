# ------------------------- Linux -------------------------
ARG image=python
ARG tag=3
FROM $image:$tag

RUN mkdir /home/pyinstaller/bootloader
WORKDIR /home/pyinstaller

COPY src bootloader/src
COPY tools bootloader/tools
COPY waf bootloader/waf
COPY wscript bootloader/wscript

COPY ..

CMD ["ls", "-l", "/home/bootloader/"]
