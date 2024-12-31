# This hook should not be loaded at all.
# `mymodule_feature2` is imported by `mymodule_main`, but the hook for `mymodule_main` explicitly excludes
# `mymodule_feature2`. Therefore, if exclusion is applied correctly during processing of modules' imports (as opposed to
# a post-processing step), this hook will not be loaded.
raise RuntimeError("This hook should not have been loaded!")
