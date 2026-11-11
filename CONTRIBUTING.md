# Contributing to X28 Flasher

[User quick start](README.md#quick-start) · [Usage guide](docs/USAGE.md)

Bug reports, documentation fixes and focused pull requests are welcome. For a larger change, open an issue first so we can agree on the scope.

## Report a bug

Include the app version, OS/architecture, action, relevant slot, exact error and how to reproduce it.
For a hardware run, say whether a write was attempted and preserve the run folder. Do not retry a stopped write just to reproduce it.

**Never publish firmware dumps, full backups, passwords, private keys or unredacted device identifiers.** Use synthetic data in fixtures.

## Make a pull request

1. Fork the repository and create a branch from `main`.
2. Make the smallest complete change. Update affected callers, tests and documentation.
3. Run the relevant tests below. For UI/packaging changes, check the installed app on the affected platform too.
4. Open a PR explaining the change, tests performed and any hardware/platform behavior you did **not** test.
5. Use a Conventional Commit title, such as `fix(usb): handle a short read`, `feat(gui): add an action`, or `docs: simplify setup`.

No real modem is needed for ordinary unit tests. Hardware testing is separate and always requires the owner's explicit approval.

## Find the code

| Path | Purpose |
|---|---|
| `tools/x28-flasher/gui/index.html` | Shared desktop UI |
| `tools/x28-flasher/gui.py`, `session_host.py` | Local API, jobs, prompts and the held USB session |
| `tools/x28-flasher/native/` | macOS, Windows and Linux desktop windows |
| `tools/x28-flasher/wizard.py`, `x28_flasher.py` | Terminal entry points and guided actions |
| `tools/recovery/` | USB reads, backups, validation, write/read-back and recovery tools |
| `tools/build/` | Image assembly and stock SSH integration |
| `tools/firmware/` | Container definition and firmware inventory |
| `.github/workflows/ci.yml` | Platform tests, builds, installers and releases |

Firmware images and assembly bundles come from [zlt-x28-openwrt releases](https://github.com/mralinp/zlt-x28-openwrt/releases).
The repo does not need a copy of the firmware source for normal packaged-app use.

## Run from source

Use Python 3.10+; CI uses **Python 3.14**. You also need Git and libusb.

```bash
git clone https://github.com/mralinp/x28-flasher.git
cd x28-flasher
```

On macOS, install libusb with `brew install libusb`. On Debian/Ubuntu, use `sudo apt install libusb-1.0-0 python3-venv`.
Then, on macOS/Linux:

```bash
python3 tools/recovery/setup_mtkclient.py
python3 tools/x28-flasher/x28_flasher.py         # developer browser UI
python3 tools/x28-flasher/x28_flasher.py wizard  # terminal menu, instead
```

The setup helper installs the pinned, patched mtkclient into `private/` and currently uses Unix venv paths.
For Windows, use the build procedure below rather than that helper; install `pywinpty==3.1.2` in the Python environment used for Windows GUI tests.
Windows source checkouts should use SSH keys; password prompts use the packaged app's executable helper.
The source browser UI and packaged native windows share the same page and backend.

The download agent is already at `tools/x28-flasher/assets/DA_BR.bin`; builds check its expected SHA-256.
Do not replace the pinned mtkclient or edit its installed library by hand to bypass identity checks.

## Run tests

Tests are standalone Python files. Run a relevant file while working, for example:

```bash
python3 tools/x28-flasher/test_gui.py
python3 tools/recovery/test_slot_session.py
node tools/x28-flasher/gui/test_releases.cjs  # release-list rendering; requires Node.js
```

Image-assembly tests also need the firmware's package files. Download an `x28-assembly-*.tar.gz` asset from a
[firmware release](https://github.com/mralinp/zlt-x28-openwrt/releases), extract it, and set `X28_OVERLAY` to its `overlay/` folder
(the directory containing `package/`). Alternatively, use the firmware checkout root containing `package/`.
CI downloads these inputs automatically; missing files locally are not fixed by skipping the tests.

Run the full Python suite from the repo root (Bash; use Git Bash on Windows):

```bash
export X28_OVERLAY=/absolute/path/to/extracted/overlay
failed=0
for test in tools/build/test_*.py tools/recovery/test_*.py tools/x28-flasher/test_*.py; do
  python3 "$test" || failed=1
done
python3 tools/recovery/common.py || failed=1
test "$failed" -eq 0
```

These tests use fake devices and synthetic data. Do not point routine tests at a modem or add automatic hardware writes to CI.

## Build the app

Build **on the target OS**; these are not cross-build commands. CI is the reference for exact dependencies and packaging:
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### 1. Prepare the pinned source and build environment

Install Python 3.14 and Git. Add libusb as above on macOS/Linux. Run this in Bash (Git Bash on Windows):

```bash
COMMIT="$(python3 -c "import sys; sys.path.insert(0, 'tools/recovery'); import common; print(common.MTKCLIENT_COMMIT)")"
mkdir -p bh/src
git -C bh/src init -q
git -C bh/src fetch -q --depth 1 https://github.com/bkerler/mtkclient.git "$COMMIT"
git -C bh/src -c advice.detachedHead=false -c core.autocrlf=false checkout -q FETCH_HEAD
python3 -m venv bh/venv
PY=bh/venv/bin/python
# On Windows instead: PY=bh/venv/Scripts/python
"$PY" -m pip install pycryptodome pycryptodomex pyserial pyusb colorama questionary pyinstaller
# Windows also needs: "$PY" -m pip install libusb pywinpty==3.1.2
```

Keep `bh/src` clean; the build installs and patches the copy in the venv, not the source checkout.

### 2. Build and smoke-test the backend

```bash
"$PY" tools/x28-flasher/build_binary.py --home bh --out dist --version 0.0.0
B=dist/x28-flasher/x28-flasher
# On Windows instead: B=dist/x28-flasher/x28-flasher.exe
"$B" --selftest
"$B" --run-script tools/x28-flasher/smoke_gui.py
```

These smoke tests do not flash hardware. Close an existing app/session before testing packaged launchers.

### 3. Package the native desktop window

**macOS, Apple silicon** — install Xcode Command Line Tools for `swiftc`:

```bash
python3 tools/x28-flasher/build_app.py
hdiutil create -volname "X28 Flasher" -srcfolder "dist/X28 Flasher.app" -ov -format UDZO X28-Flasher-macos-arm64.dmg
```

**Linux x86_64** — the package includes the GTK/WebKit launcher and declares its APT dependencies:

```bash
tools/x28-flasher/installers/make_deb.sh dist 0.0.0 X28-Flasher-linux-x86_64.deb
```

**Windows x64** — install Inno Setup 6; the native launcher also uses the Windows .NET Framework compiler and PowerShell:

```bash
python3 tools/x28-flasher/build_windows.py
"/c/Program Files (x86)/Inno Setup 6/ISCC.exe" "//DSrc=$(cygpath -w "$PWD/dist/x28-flasher")" "//DOut=$(cygpath -w "$PWD")" "//DVersion=0.0.0" tools/x28-flasher/installers/windows.iss
```

The Windows build downloads a pinned, checksum-checked WebView2 SDK and Microsoft's signature-checked Runtime bootstrapper.
CI installs the Linux and Windows packages and tests their actual native windows. Those installer smoke tests install software and open windows;
use a disposable environment, following the workflow's commands. Linux's test uses Xvfb/DBus rather than a physical display.

Build output (`dist/`, `build-x28-flasher/`, `bh/`) and private data are git-ignored. Do not commit installers or local build artifacts.

## Safety rules for changes

- Keep input validation, unit/loader identity checks, typed confirmation, write acknowledgement and read-back verification intact.
- Never turn a rehearsal into a silent real-image write. A rehearsal itself writes the backed-up image.
- Do not add automatic write retries, slot switches or reboots after failures.
- Plain desktop A/B flashes intentionally use target read-back checks without requiring the old contents to equal the backup. Do not confuse this with recovery tools' stronger checks.
- Preserve errors and write-attempt journals. For receipt-bound operations, changing recovery tools invalidates earlier tool identities; do not edit them mid-chain.
- Keep private data and signing/SSH keys out of code, fixtures, logs attached to issues and commits.
- Do not claim hardware support from a mocked test or headless UI test. State exactly what was tested.

## Releases and licensing

After a merge to `main`, CI derives the next version from Conventional Commits, tests all three platforms, and publishes only when every build passes
and all three installers are present. Versions below 1.0 are marked as GitHub pre-releases. See [`scripts/release.py`](scripts/release.py).

Follow [LICENSE](LICENSE) and retain third-party notices. The vendor download agent is a bundled third-party binary; do not assume the project's
license grants new rights to redistribute that component or firmware dumps.
