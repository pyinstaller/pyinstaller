# This hook should not be loaded at all.
# `mymodule_feature3` is imported by `mymodule_main.submodule_feature3` via import of `mymodule_feature3.submodule1`,
# but the hook for `mymodule_main` explicitly excludes `mymodule_feature3`. Therefore, if exclusion is applied correctly
# during processing of modules' imports (as opposed to a post-processing step), and if exclusion rules are applied in
# recursive way, this hook will not be loaded.
raise RuntimeError("This hook should not have been loaded!")
