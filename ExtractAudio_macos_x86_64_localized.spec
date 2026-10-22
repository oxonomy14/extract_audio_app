# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import certifi

# Extract Audio — macOS Intel (x86_64)
# Build on an Intel Mac with native x86_64 Python and an Intel FFmpeg binary.
project_dir = Path.cwd()
ffmpeg_path = Path.home() / "bin" / "ffmpeg"
main_script = project_dir / "main_macos_x86_64_localized.py"
icon_path = project_dir / "ExtractAudio.icns"
help_path = project_dir / "HELP_en.md"
architecture = "x86_64"
architecture_priority = ["x86_64"]

for required_path, description in (
    (ffmpeg_path, "FFmpeg"),
    (main_script, main_script.name),
    (icon_path, "ExtractAudio.icns"),
    (project_dir / "HELP_en.md", "HELP_en.md"),
    (project_dir / "HELP_uk.md", "HELP_uk.md"),
    (project_dir / "HELP_ru.md", "HELP_ru.md"),
):
    if not required_path.is_file():
        raise FileNotFoundError(f"{description} not found: {required_path}")

bundle_version = "1"
info_plist = {
    "CFBundleDisplayName": "Extract Audio",
    "CFBundleName": "Extract Audio",
    "CFBundleIdentifier": "dev.andriiweb.extractaudio",
    "CFBundleShortVersionString": "0.2.0",
    "CFBundleVersion": bundle_version,
    "LSArchitecturePriority": architecture_priority,
    "NSHumanReadableCopyright": "Copyright © 2026 Andrii Semenenko",
}

a = Analysis(
    [str(main_script)],
    pathex=[str(project_dir)],
    binaries=[(str(ffmpeg_path), ".")],
    datas=[
        (certifi.where(), "."),
        (str(project_dir / "HELP_en.md"), "."),
        (str(project_dir / "HELP_uk.md"), "."),
        (str(project_dir / "HELP_ru.md"), "."),
    ],
    hiddenimports=[
        "yt_dlp",
        "yt_dlp.version",
        "yt_dlp.compat",
        "yt_dlp.extractor",
        "yt_dlp.extractor.vimeo",
        "yt_dlp.extractor.youtube",
        "certifi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ExtractAudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=architecture,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Extract Audio",
)
app = BUNDLE(
    coll,
    name="Extract Audio.app",
    icon=str(icon_path),
    bundle_identifier="dev.andriiweb.extractaudio",
    info_plist=info_plist,
)
