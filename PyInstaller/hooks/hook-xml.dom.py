# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
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

import string
attrs = [('Node', 0),
         ('INDEX_SIZE_ERR', 1),
         ('DOMSTRING_SIZE_ERR', 2),
         ('HIERARCHY_REQUEST_ERR', 3),
         ('WRONG_DOCUMENT_ERR', 4),
         ('INVALID_CHARACTER_ERR ', 5),
         ('NO_DATA_ALLOWED_ERR', 6),
         ('NO_MODIFICATION_ALLOWED_ERR', 7),
         ('NOT_FOUND_ERR', 8),
         ('NOT_SUPPORTED_ERR', 9),
         ('INUSE_ATTRIBUTE_ERR', 10),
         ('INVALID_STATE_ERR', 11),
         ('SYNTAX_ERR', 12),
         ('INVALID_MODIFICATION_ERR', 13),
         ('NAMESPACE_ERR', 14),
         ('INVALID_ACCESS_ERR', 15),
         ('DOMException', 0),
         ('IndexSizeErr', 0),
         ('DomstringSizeErr', 0),
         ('HierarchyRequestErr', 0),
         ('WrongDocumentErr', 0),
         ('InvalidCharacterErr', 0),
         ('NoDataAllowedErr', 0),
         ('NoModificationAllowedErr', 0),
         ('NotFoundErr', 0),
         ('NotSupportedErr', 0),
         ('InuseAttributeErr', 0),
         ('InvalidStateErr', 0),
         ('SyntaxErr', 0),
         ('InvalidModificationErr', 0),
         ('NamespaceErr', 0),
         ('InvalidAccessErr', 0),
         ('getDOMImplementation', 0),
         ('registerDOMImplementation', 0),
]

def hook(mod):
    if string.find(mod.__file__, '_xmlplus') > -1:
        mod.UNSPECIFIED_EVENT_TYPE_ERR = 0
        mod.FT_EXCEPTION_BASE = 1000
        mod.XML_PARSE_ERR = 1001
        mod.BAD_BOUNDARYPOINTS_ERR = 1
        mod.INVALID_NODE_TYPE_ERR = 2
        mod.EventException = None
        mod.RangeException = None
        mod.FtException = None
        if hasattr(mod, 'DomstringSizeErr'):
            del mod.DomstringSizeErr
        mod.DOMStringSizeErr = None
        mod.UnspecifiedEventTypeErr = None
        mod.XmlParseErr = None
        mod.BadBoundaryPointsErr = None
        mod.InvalidNodeTypeErr = None
        mod.DOMImplementation = None
        mod.implementation = None
        mod.XML_NAMESPACE = None
        mod.XMLNS_NAMESPACE = None
        mod.XHTML_NAMESPACE = None
        mod.DOMExceptionStrings = None
        mod.EventExceptionStrings = None
        mod.FtExceptionStrings = None
        mod.RangeExceptionStrings = None
    return mod
