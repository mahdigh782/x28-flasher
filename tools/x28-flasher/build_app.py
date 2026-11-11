#!/usr/bin/env python3
"""Wrap the PyInstaller output (build_binary.py) in a native macOS app: no Python, Homebrew or Setup step, and no browser.

    python build_app.py [--dist dist]      ->  dist/X28 Flasher.app

Contents/MacOS/X28 Flasher is a Swift/WKWebView window that starts the self-contained backend under Resources/backend.
Requires swiftc (Xcode Command Line Tools). The finished bundle is ad-hoc signed and verified; Developer ID signing and
Apple notarization are separate release steps, so Gatekeeper may still require Open Anyway.
"""
import argparse
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dist", type=Path, default=Path("dist"))
    args = ap.parse_args()
    src = args.dist / "x28-flasher"
    if not (src / "x28-flasher").is_file():
        raise SystemExit(f"{src}/x28-flasher not found: run build_binary.py first")
    if not shutil.which("swiftc"):
        raise SystemExit("swiftc is required: install Xcode Command Line Tools")
    app = args.dist / "X28 Flasher.app"
    shutil.rmtree(app, ignore_errors=True)
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/Resources").mkdir()
    # Keep PyInstaller's onedir layout intact: Frameworks must not contain Python data/metadata bundles.
    shutil.copytree(src, app / "Contents/Resources/backend", symlinks=True)
    shutil.copy2(HERE / "assets/AppIcon.icns", app / "Contents/Resources/AppIcon.icns")
    subprocess.run(["swiftc", "-O", "-o", str(app / "Contents/MacOS/X28 Flasher"), str(HERE / "native/main.swift"),
                    "-framework", "Cocoa", "-framework", "WebKit"], check=True)
    version = json.loads((src / "_internal/identity.json").read_text()).get("version", "dev")
    version = version if version[:1].isdigit() else "0.0.0"  # the plist wants a number; a dev build is 0.0.0
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleName": "X28 Flasher", "CFBundleDisplayName": "X28 Flasher", "CFBundleIdentifier": "com.mralinp.x28-flasher",
        "CFBundleExecutable": "X28 Flasher", "CFBundleIconFile": "AppIcon",
        "CFBundlePackageType": "APPL", "CFBundleVersion": version, "CFBundleShortVersionString": version, "NSHighResolutionCapable": True,
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},  # the window loads http://127.0.0.1
    }))
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    print(f"built {app} (native window, ad-hoc signed)")


if __name__ == "__main__":
    main()
