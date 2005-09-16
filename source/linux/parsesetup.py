# Parse Makefiles and Python Setup(.in) files.
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import re
import string


# Extract variable definitions from a Makefile.
# Return a dictionary mapping names to values.
# May raise IOError.

makevardef = re.compile('^([a-zA-Z0-9_]+)[ \t]*=(.*)')

def getmakevars(filename):
	variables = {}
	fp = open(filename)
	pendingline = ""
	try:
		while 1:
			line = fp.readline()
			if pendingline:
				line = pendingline + line
				pendingline = ""
			if not line:
				break
			if line[-2:] == '\\\n':
				pendingline = line[:-2]
			matchobj = makevardef.match(line)
			if not matchobj:
				continue
			(name, value) = matchobj.group(1, 2)
			# Strip trailing comment
			i = string.find(value, '#')
			if i >= 0:
				value = value[:i]
			value = string.strip(value)
			variables[name] = value
	finally:
		fp.close()
	return variables


# Parse a Python Setup(.in) file.
# Return two dictionaries, the first mapping modules to their
# definitions, the second mapping variable names to their values.
# May raise IOError.

setupvardef = re.compile('^([a-zA-Z0-9_]+)=(.*)')

def getsetupinfo(filename):
	modules = {}
	variables = {}
	fp = open(filename)
	pendingline = ""
	try:
		while 1:
			line = fp.readline()
			if pendingline:
				line = pendingline + line
				pendingline = ""
			if not line:
				break
			# Strip comments
			i = string.find(line, '#')
			if i >= 0:
				line = line[:i]
			if line.endswith('\\\n'):
				pendingline = line[:-2]
				continue
			matchobj = setupvardef.match(line)
			if matchobj:
				(name, value) = matchobj.group(1, 2)
				variables[name] = string.strip(value)
			else:
				words = string.split(line)
				if words:
					modules[words[0]] = words[1:]
	finally:
		fp.close()
	return modules, variables


# Test the above functions.

def test():
	import sys
	import os
	if not sys.argv[1:]:
		print 'usage: python parsesetup.py Makefile*|Setup* ...'
		sys.exit(2)
	for arg in sys.argv[1:]:
		base = os.path.basename(arg)
		if base[:8] == 'Makefile':
			print 'Make style parsing:', arg
			v = getmakevars(arg)
			prdict(v)
		elif base[:5] == 'Setup':
			print 'Setup style parsing:', arg
			m, v = getsetupinfo(arg)
			prdict(m)
			prdict(v)
		else:
			print arg, 'is neither a Makefile nor a Setup file'
			print '(name must begin with "Makefile" or "Setup")'

def prdict(d):
	keys = d.keys()
	keys.sort()
	for key in keys:
		value = d[key]
		print "%-15s" % key, str(value)

if __name__ == '__main__':
	test()
