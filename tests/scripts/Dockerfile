FROM python:2.7

RUN mkdir -p /src

ADD requirements.txt tests/requirements-*.txt /src/
RUN pip install \
    -r /src/requirements.txt \
    -r /src/requirements-tools.txt \
    -r /src/requirements-libraries.txt

ADD *.py setup.cfg README.rst MANIFEST.in .pylintrc /src/
ADD PyInstaller /src/PyInstaller
ADD bootloader /src/bootloader
ADD doc /src/doc

RUN rm -rf /src/PyInstaller/bootloader/*

WORKDIR /src/bootloader
RUN python waf distclean all

WORKDIR /src
RUN python setup.py install

ADD tests /src/tests
