#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import os
import shutil

import pytest

from PyInstaller import HOMEPATH, PLATFORM
from PyInstaller.utils.tests import importorskip

from PyInstaller.utils.win32 import winmanifest

#- Helpers


# Go from current DOM element to the top-level node, and collect element tags along the way. Then reverse the list so
# it goes from top-level element to the current one.
def _get_parent_tags(node):
    tags = []
    while node is not None:
        tags.append(node.tag)
        node = node.getparent()
    return list(reversed(tags))


# Remove the whitespace and newline change actions
def _filter_whitespace_changes(actions):
    import xmldiff.actions

    filtered_actions = []
    for action in actions:
        # Skip text updates that involve only whitespace. This involves both trailing text and text within the nodes.
        if isinstance(action, (xmldiff.actions.UpdateTextAfter, xmldiff.actions.UpdateTextIn)):
            if not action.text.strip():
                continue
        filtered_actions.append(action)
    return filtered_actions


# List of element tags from top-level <assembly> to <requestedExecutionLevel> for UAC settings.
_REQUEST_EXECUTION_LEVEL_TAGS = [
    '{urn:schemas-microsoft-com:asm.v1}assembly',
    '{urn:schemas-microsoft-com:asm.v3}trustInfo',
    '{urn:schemas-microsoft-com:asm.v3}security',
    '{urn:schemas-microsoft-com:asm.v3}requestedPrivileges',
    '{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel',
]

# List of element tags from top-level <assembly> to <assemblyIdentity> for dependent assemblies.
_DEPENDENT_ASSEMBLY_IDENTITY_TAGS = [
    '{urn:schemas-microsoft-com:asm.v1}assembly',
    '{urn:schemas-microsoft-com:asm.v1}dependency',
    '{urn:schemas-microsoft-com:asm.v1}dependentAssembly',
    '{urn:schemas-microsoft-com:asm.v1}assemblyIdentity',
]

_MS_COMMON_CONTROLS_ATTRIBUTES = {
    "type": "win32",
    "name": "Microsoft.Windows.Common-Controls",
    "version": "6.0.0.0",
    "processorArchitecture": "*",
    "publicKeyToken": "6595b64144ccf1df",
    "language": "*",
}

#- Tests with default manifest template


# Generate default application manifest, which should be the same as the default XML template.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_default_manifest():
    import lxml
    import xmldiff.main

    app_manifest = winmanifest.create_application_manifest()

    tree_base = lxml.etree.fromstring(winmanifest._DEFAULT_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)

    # There should be no difference, as unmodified copy of template is returned.
    assert not diff


# Generate application manifest with uac_admin=True.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_default_manifest_uac_admin():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    app_manifest = winmanifest.create_application_manifest(uac_admin=True)

    tree_base = lxml.etree.fromstring(winmanifest._DEFAULT_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)

    # We expect exactly one change. The `level` attribute of `requestedExecutionLevel` element should be changed to
    # `requireAdministrator`.
    assert len(diff) == 1

    action = diff[0]
    assert isinstance(action, xmldiff.actions.UpdateAttrib)
    assert action.name == 'level'
    assert action.value == 'requireAdministrator'

    node = tree.xpath(action.node)[0]  # The node in xmldiff action is xpath
    assert _get_parent_tags(node) == _REQUEST_EXECUTION_LEVEL_TAGS


# Generate application manifest with uac_uiaccess=True.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_default_manifest_uac_uiaccess():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    app_manifest = winmanifest.create_application_manifest(uac_uiaccess=True)

    tree_base = lxml.etree.fromstring(winmanifest._DEFAULT_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)

    # We expect exactly one change. The `uiAccess` attribute of `requestedExecutionLevel` element should be changed to
    # `true`.
    assert len(diff) == 1

    action = diff[0]
    assert isinstance(action, xmldiff.actions.UpdateAttrib)
    assert action.name == 'uiAccess'
    assert action.value == 'true'

    node = tree.xpath(action.node)[0]  # The node in xmldiff action is xpath
    assert _get_parent_tags(node) == _REQUEST_EXECUTION_LEVEL_TAGS


# Generate application manifest with both uac_admin=True and uac_uiaccess=True.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_default_manifest_uac_admin_and_uiaccess():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    app_manifest = winmanifest.create_application_manifest(uac_admin=True, uac_uiaccess=True)

    tree_base = lxml.etree.fromstring(winmanifest._DEFAULT_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)

    # We expect exactly two changes. The `level` attribute of `requestedExecutionLevel` element should be changed to
    # `requireAdministrator` and the `uiAccess` attribute of `requestedExecutionLevel` element should be changed to
    # `true`.
    assert len(diff) == 2

    # First change action
    action = diff[0]
    assert isinstance(action, xmldiff.actions.UpdateAttrib)
    assert action.name == 'level'
    assert action.value == 'requireAdministrator'

    node = tree.xpath(action.node)[0]  # The node in xmldiff action is xpath
    assert _get_parent_tags(node) == _REQUEST_EXECUTION_LEVEL_TAGS

    # Second change action
    action = diff[1]
    assert isinstance(action, xmldiff.actions.UpdateAttrib)
    assert action.name == 'uiAccess'
    assert action.value == 'true'

    node = tree.xpath(action.node)[0]
    assert _get_parent_tags(node) == _REQUEST_EXECUTION_LEVEL_TAGS


#- Tests with custom manifest template


# Generate application manifest from template that has no <trustInfo> element, which we need to add to store the
# uac_admin and uac_uiaccess settings (even if left at default).
# The manifest also contains a `dpiAwareness` setting, which should be preserved (the old PyInstaller < 6.0 manifest
# handling code had no notion of this element, so it ended up striping it away).
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_custom_manifest_no_trust_info():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    _MANIFEST_XML = \
b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"></supportedOS>
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"></supportedOS>
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"></supportedOS>
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"></supportedOS>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"></supportedOS>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, unaware</dpiAwareness>
    </windowsSettings>
  </application>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"></assemblyIdentity>
    </dependentAssembly>
  </dependency>
</assembly>
"""  # noqa: E128,E501

    app_manifest = winmanifest.create_application_manifest(_MANIFEST_XML)

    tree_base = lxml.etree.fromstring(_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)
    diff = _filter_whitespace_changes(diff)

    # After filtering newline/whitespace changes, modification still involves several steps.
    assert len(diff) == 6

    action = diff[0]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert tree.xpath(action.target)[0].tag == _REQUEST_EXECUTION_LEVEL_TAGS[0]
    assert action.tag == _REQUEST_EXECUTION_LEVEL_TAGS[1]

    action = diff[1]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _REQUEST_EXECUTION_LEVEL_TAGS[2]

    action = diff[2]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _REQUEST_EXECUTION_LEVEL_TAGS[3]

    action = diff[3]
    print(action)
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _REQUEST_EXECUTION_LEVEL_TAGS[4]

    action = diff[4]
    assert isinstance(action, xmldiff.actions.InsertAttrib)
    assert action.name == 'level'
    assert action.value == 'asInvoker'

    action = diff[5]
    assert isinstance(action, xmldiff.actions.InsertAttrib)
    assert action.name == 'uiAccess'
    assert action.value == 'false'


# Generate application manifest from template that has no dependent assembly for MS Common Controls, which we need to
# add.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_custom_manifest_no_ms_common_controls():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    _MANIFEST_XML = \
b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"></requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"></supportedOS>
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"></supportedOS>
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"></supportedOS>
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"></supportedOS>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"></supportedOS>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, unaware</dpiAwareness>
    </windowsSettings>
  </application>
</assembly>
"""  # noqa: E128,E501

    app_manifest = winmanifest.create_application_manifest(_MANIFEST_XML)

    tree_base = lxml.etree.fromstring(_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)
    diff = _filter_whitespace_changes(diff)

    # After filtering newline/whitespace changes, modification still involves several steps.
    assert len(diff) == 9

    action = diff[0]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert tree.xpath(action.target)[0].tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[0]
    assert action.tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[1]

    action = diff[1]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[2]

    action = diff[2]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[3]

    # We do not care about insertion order, just that all attributes are added
    added_attributes = {}
    for action in diff[3:]:
        assert isinstance(action, xmldiff.actions.InsertAttrib)
        added_attributes[action.name] = action.value

    assert added_attributes == _MS_COMMON_CONTROLS_ATTRIBUTES


# Generate application manifest from template that has dependent assembly for MS Common Controls, but its attributes
# differ from our defaults.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_custom_manifest_different_ms_common_controls():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    _MANIFEST_XML = \
b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"></requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"></supportedOS>
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"></supportedOS>
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"></supportedOS>
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"></supportedOS>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"></supportedOS>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, unaware</dpiAwareness>
    </windowsSettings>
  </application>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="5.0.0.0"></assemblyIdentity>
    </dependentAssembly>
  </dependency>
</assembly>
"""  # noqa: E128,E501

    app_manifest = winmanifest.create_application_manifest(_MANIFEST_XML)

    tree_base = lxml.etree.fromstring(_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)
    diff = _filter_whitespace_changes(diff)

    # After filtering newline/whitespace changes, modification still involves several steps:
    # one attribute modification (version) and three attribute additions.
    assert len(diff) == 4

    updated_attributes = {}
    added_attributes = {}
    for action in diff:
        if isinstance(action, xmldiff.actions.UpdateAttrib):
            updated_attributes[action.name] = action.value
        elif isinstance(action, xmldiff.actions.InsertAttrib):
            added_attributes[action.name] = action.value
        else:
            raise ValueError(f"Unexpected modification: {action}")

        assert tree.xpath(action.node)[0].tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[-1]

    assert updated_attributes == {'version': _MS_COMMON_CONTROLS_ATTRIBUTES['version']}
    assert added_attributes == {
        key: value
        for key, value in _MS_COMMON_CONTROLS_ATTRIBUTES.items()
        if key in ("processorArchitecture", "publicKeyToken", "language")
    }


# Generate application manifest from template that has dependent assembly for a custom library, but not for MS Common
# Controls. This is essentially the same as `test_manifest_custom_manifest_no_ms_common_controls`, but we should not
# touch the existing dependent assembly.
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_custom_manifest_no_ms_common_controls_with_custom_dependency():
    import lxml
    import xmldiff.main
    import xmldiff.actions

    _MANIFEST_XML = \
b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"></requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"></supportedOS>
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"></supportedOS>
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"></supportedOS>
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"></supportedOS>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"></supportedOS>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, unaware</dpiAwareness>
    </windowsSettings>
  </application>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="MyAwesomeLibrary" version="1.0.0.0"></assemblyIdentity>
    </dependentAssembly>
  </dependency>
</assembly>
"""  # noqa: E128,E501

    app_manifest = winmanifest.create_application_manifest(_MANIFEST_XML)

    tree_base = lxml.etree.fromstring(_MANIFEST_XML)
    tree = lxml.etree.fromstring(app_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)
    diff = _filter_whitespace_changes(diff)

    # After filtering newline/whitespace changes, modification still involves several steps.
    assert len(diff) == 9

    action = diff[0]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert tree.xpath(action.target)[0].tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[0]
    assert action.tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[1]

    action = diff[1]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[2]

    action = diff[2]
    assert isinstance(action, xmldiff.actions.InsertNode)
    assert action.tag == _DEPENDENT_ASSEMBLY_IDENTITY_TAGS[3]

    # We do not care about insertion order, just that all attributes are added
    added_attributes = {}
    for action in diff[3:]:
        assert isinstance(action, xmldiff.actions.InsertAttrib)
        added_attributes[action.name] = action.value

    assert added_attributes == _MS_COMMON_CONTROLS_ATTRIBUTES


#- Test application manifest embedding and retrieval.
# Works only on Windows, because we need to test with actual executable with actual exeutable.


@pytest.mark.win32
def test_manifest_write_to_exe(tmp_path):
    # Locate bootloader executable
    bootloader_file = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, 'run.exe')

    # Create a local copy
    test_file = str(tmp_path / 'test_file.exe')
    shutil.copyfile(bootloader_file, test_file)

    # Create manifest
    app_manifest = winmanifest.create_application_manifest(uac_admin=False, uac_uiaccess=True)

    # ... embed it, ...
    winmanifest.write_manifest_to_executable(test_file, app_manifest)

    # ... and read it back
    read_manifest = winmanifest.read_manifest_from_executable(test_file)

    # These should be identical, byte-for-byte
    assert read_manifest == app_manifest


# Similar to test_manifest_write_to_exe, but using custom manifest with non-ASCII characters.
@pytest.mark.win32
@importorskip('lxml')
@importorskip('xmldiff')
def test_manifest_write_to_exe_non_ascii_characters(tmp_path):
    import lxml
    import xmldiff.main
    import xmldiff.actions

    _MANIFEST_XML = \
"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity name="日本語で書かれた名前" processorArchitecture="amd64" type="win32" version="1.0.0.0"/>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity language="*" name="Microsoft.Windows.Common-Controls" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" type="win32" version="6.0.0.0"/>
    </dependentAssembly>
  </dependency>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"/>
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/>
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
""".encode("utf-8")  # noqa: E128,E501

    # Locate bootloader executable
    bootloader_file = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, 'run.exe')

    # Create a local copy
    test_file = str(tmp_path / 'test_file.exe')
    shutil.copyfile(bootloader_file, test_file)

    # Create manifest
    app_manifest = winmanifest.create_application_manifest(_MANIFEST_XML, uac_admin=False, uac_uiaccess=False)

    # ... embed it, ...
    winmanifest.write_manifest_to_executable(test_file, app_manifest)

    # ... and read it back
    read_manifest = winmanifest.read_manifest_from_executable(test_file)

    # These should be identical, byte-for-byte
    assert read_manifest == app_manifest

    # The retrieved manifest should have equivalent DOM to the original XML.
    # The raw string might differ from the original template due to closing tags.
    tree_base = lxml.etree.fromstring(_MANIFEST_XML)
    tree = lxml.etree.fromstring(read_manifest)

    diff = xmldiff.main.diff_trees(tree_base, tree)
    diff = _filter_whitespace_changes(diff)

    assert not diff
