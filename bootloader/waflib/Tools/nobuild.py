#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! https://waf.io/book/index.html#_obtaining_the_waf_file

from waflib import Task


def build(bld):
    def run(self):
        for x in self.outputs:
            x.write('')

    for (name, cls) in Task.classes.items():
        cls.run = run
