#!/usr/bin/env bash

set -e

main() {
    local tools_dir="$1"
    local tmp_dir="$2"
    local app_name="$3"
    local app_id="org.pyinstaller.appimage.test"
    local app_dir="${tmp_dir}/dist/AppRun"

    echo ">>> Adjusting file names to fit in the AppImage"
    [ -d "${app_dir}" ] && rm -rf "${app_dir}"
    mv -v "${tmp_dir}/dist/${app_name}" "${app_dir}"
    mv -v "${app_dir}/${app_name}" "${app_dir}/AppRun"

    echo ">>> Copying icons"
    cp -v "${tools_dir}/DirIcon.png" "${app_dir}/.DirIcon"
    cp -v "${tools_dir}/AppIcon.svg" "${app_dir}/${app_name}.svg"

    echo ">>> Copying metadata files"
    mkdir -pv "${app_dir}/usr/share/metainfo"
    cp -v "${tools_dir}/${app_id}.appdata.xml" "${app_dir}/usr/share/metainfo"
    mkdir -pv "${app_dir}/usr/share/applications"
    cp -v "${tools_dir}/${app_id}.desktop" "${app_dir}/usr/share/applications"
    ln -srv "${app_dir}/usr/share/applications/${app_id}.desktop" "${app_dir}/${app_id}.desktop"

    return 0  # <-- Needed, do not remove!
}

main "$@"
