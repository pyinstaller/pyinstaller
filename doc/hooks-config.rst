===============================
Hook Configuration Options
===============================

As of version 4.4, |PyInstaller| implements a mechanism for passing
configuration options to the hooks. At the time of writing, this
feature is supported only in :ref:`.spec files <using spec files>` and
has no command-line interface equivalent.

The hook configuration options consist of a dictionary that is passed
to the ``Analysis`` object via the ``hooksconfig`` argument. The keys
of the dictionary represent `hook identifiers` while the values are
dictionaries of hook-specific keys and values that correspond to
hook settings:


.. code-block:: python

    a = Analysis(
        ["program.py"],
        ...,
        hooksconfig={
            "some_hook_id": {
                "foo": ["entry1", "entry2"],
                "bar": 42,
                "enable_x": True,
            },
            "another_hook_id": {
                "baz": "value",
            },
        },
        ...,
    )


.. _supported hooks and options:

Supported hooks and options
===========================

This section lists hooks that implement support for configuration
options. For each hook (or group of hooks), we provide the `hook
identifier` and the list of supported options.

GObject introspection (gi) hooks
--------------------------------

The options passed under `gi` hook identifier control the collection
of GLib/Gtk resources (themes, icons, translations) in various
hooks related to ``GObject introspection`` (i.e., ``hook-gi.*``).

They are especially useful when freezing ``Gtk3``-based applications on
linux, as they allow one to limit the amount of themes and icons collected
from the system ``/usr/share`` directory.

**Hook identifier:** ``gi``

**Options**

 * ``languages`` [*list of strings*]: list of locales (e.g., ˙en_US˙) for
   which translations should be collected. By default, ``gi`` hooks
   collect all available translations.

 * ``icons`` [*list of strings*]: list of icon themes (e.g., `Adwaita`)
   that should be collected. By default, ``gi`` hooks collect all available
   icon themes.

 * ``themes`` [*list of strings*]: list of Gtk themes (e.g., `Adwaita`)
   that should be collected. By default, ``gi`` hooks collect all available
   icon themes.

 * ``module-versions`` [*dict of version strings*]: versions of gi modules to
   use. For example, a key of 'GtkSource' and value to '4' will use
   gtksourceview4.

**Example**

Collect only ``Adwaita`` theme and icons, limit the collected
translations to British English and Simplified Chinese, and use
version 3.0 of Gtk and version 4 of GtkSource:

.. code-block:: python

    a = Analysis(
        ["my-gtk-app.py"],
        ...,
        hooksconfig={
            "gi": {
                "icons": ["Adwaita"],
                "themes": ["Adwaita"],
                "languages": ["en_GB", "zh_CN"],
                "module-versions": {
                    "Gtk": "3.0",
                    "GtkSource": "4",
                },
            },
        },
        ...,
    )

.. note:: Currently only the ``module-versions`` configuration is available for ``GtkSource``.


Adding an option to the hook
============================

Implementing support for hook options requires access to ``hook_api``
object, which is available only when hook implements the ``hook(hook_api)``
function (as described :ref:`here <The hook(hook_api) Function>`).

The value of a hook's configuration option can be obtained using the
:func:`~PyInstaller.utils.hooks.get_hook_config` function:

.. code-block:: python

    # hook-mypackage.py
    from PyInstaller.utils.hooks import get_hook_config

    # Processing unrelated to hook options, using global hook values
    binaries, datas, hiddenimports = ...

    # Collect extra data
    def hook(hook_api):
        # Boolean option 'collect_extra_data'
        if get_hook_config(hook_api, 'mypackage', 'collect_extra_data'):
            extra_datas = ...  # Collect extra data
            hook_api.add_datas(extra_datas)


After implementing option handling in the hook, please add a section
documenting it under :ref:`supported hooks and options`, to inform
the users of the option's availability and the meaning of its value(s).

The above hook example allows the user to toggle the collection of extra
data from ``mypackage`` by setting the corresponding option in their
:ref:`.spec file <using spec files>`:

.. code-block:: python

    a = Analysis(
        ["program-using-mypackage.py"],
        ...,
        hooksconfig={
            "mypackage": {
                "collect_extra_data": True,
            },
        },
        ...,
    )


.. include:: _common_definitions.txt

.. Emacs config:
 Local Variables:
 mode: rst
 ispell-local-dictionary: "american"
 End:
