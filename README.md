# x28-flasher

Backup, verify and guarded flashing tools for the ZLT X28 5G CPE (MediaTek MT6890). The firmware itself lives in
[mralinp/zlt-x28-openwrt](https://github.com/mralinp/zlt-x28-openwrt); its docs (`docs/RECOVERY.md`, `docs/BUILD.md`,
`docs/research/`) describe the procedures these tools implement.

- `tools/recovery/`: backup and verify, mtkclient setup, USB reads, and the guarded flash sessions (dry run first, typed phrase per step). Do not edit these mid-chain: their hashes bind the receipts.
- `tools/x28-flasher/`: the wizard and the single-binary build (PyInstaller). Frozen builds are read-only.
- `firmware/`: git submodule of the firmware repo, pinned. `tools/build` is a symlink into it (`package_ubi.py`, `stage_native.py`, `ab_guard.py`, `first_boot.py`, the tools Dockerfile).

```
git clone --recurse-submodules git@github.com:mralinp/x28-flasher.git
for t in tools/recovery/test_*.py tools/x28-flasher/test_*.py; do python3 "$t"; done
```

Flashable images are downloaded from the firmware repo's releases. The vendor download agent and any firmware dumps are never committed.
Licence: GPL-2.0-only.
