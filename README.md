<div align="center">

<img src="docs/assets/logo.svg" alt="X28 Flasher" width="100">

# X28 Flasher

Back up and flash your **ZLT X28 5G modem (MediaTek MT6890 / T750)** from a desktop app.

[Download](https://github.com/mralinp/x28-flasher/releases) · [Quick start](#quick-start) · [Full guide](docs/USAGE.md) · [Contribute](CONTRIBUTING.md)

[![CI](https://github.com/mralinp/x28-flasher/actions/workflows/ci.yml/badge.svg)](https://github.com/mralinp/x28-flasher/actions/workflows/ci.yml)

</div>

<a id="warning"></a>
> [!WARNING]
> Flashing can leave your modem unable to boot. **Make a verified backup and keep a second copy on another disk before writing.**
> Keep power and USB connected until the operation finishes. Stop or closing the app cannot undo a write.
> A UART adapter is recommended for diagnosing boot problems. Not affiliated with ZLT, Tozed, MediaTek or Quectel.

![X28 Flasher](docs/screenshot.png)

## Install

Download the package for your computer from **[Releases](https://github.com/mralinp/x28-flasher/releases)**.
Each supported platform has its own desktop window.

| Your computer | Download | Install and open |
|---|---|---|
| Windows 10 (1809+) / 11, x64 | `X28-Flasher-windows-x64-setup.exe` | Run setup, then open **X28 Flasher** from Start. |
| macOS, Apple silicon | `X28-Flasher-macos-arm64.dmg` | Drag the app to Applications. It is unsigned; first launch with right-click → **Open**. |
| Linux x86_64, Debian/Ubuntu-compatible | `X28-Flasher-linux-x86_64.deb` | Run `sudo apt install ./X28-Flasher-linux-x86_64.deb`, then open **X28 Flasher** from the menu. |

No cloning, pip setup or separate download agent is needed. The modem tools and `DA_BR.bin` are bundled.

- **Windows:** setup installs WebView2 if missing (internet required). The modem's download interface may also need a compatible WinUSB driver.
- **Linux:** APT installs the GTK/WebKit dependencies. Tested on Ubuntu 22.04; WebKitGTK 4.1 must be available, as on Debian 12+.
- **Docker is only needed** for **Build from my backup** and **Root access**. Downloading and flashing a signed image needs no Docker.
- **Boot order** needs root SSH access to the running modem and an OpenSSH client on your computer. See the [full guide](docs/USAGE.md#boot-order).

## Quick start

You need the X28, its power supply, a USB data cable, and enough disk space for a full backup.

1. **Connect device.** Connect USB and follow the app's power-off/wait/power-on prompts. The device panel shows the stored boot slot.
2. **Backup.** Choose a writable folder (for example, under Documents), let verification finish, then copy the backup to another disk. Keep this unit's backup for recovery.
3. **Get an image.** Download a signed firmware image. Stable releases are shown by default; tick **Include beta releases** if you want pre-releases too.
4. **Choose the write slot.** In **Flash OpenWrt**, select the image, your backup, and **A or B**. Flashing replaces that slot; it **does not change boot order**.
5. **Flash.** Rehearsal is optional and writes the backed-up image, not the new firmware. Turn **Rehearsal off for the real write**, accept the checklist, and type the exact phrase requested. Wait for successful read-back verification.
6. **Boot the modem.** Disconnect the USB session, then power-cycle when ready. If you wrote the other slot, you must change **Boot order** separately using root SSH access.

**Root access is optional**, not a prerequisite for a USB flash. If you need SSH on stock firmware to change boot order, prepare it before flashing; see the [manual](docs/USAGE.md#root-access).

If a step fails, keep the run folder and logs. **Do not blindly retry a write, switch slots or reboot after a stopped write.**
Use the [full guide and recovery references](docs/USAGE.md#troubleshooting).

## Help and contribute

- [Full usage guide](docs/USAGE.md): each action, boot order, logs and troubleshooting.
- [Contributing guide](CONTRIBUTING.md): source setup, tests, builds and pull requests.
- [Report a problem](https://github.com/mralinp/x28-flasher/issues): include the app version, OS, failed step and error; redact device identifiers and secrets.
- [Firmware project](https://github.com/mralinp/zlt-x28-openwrt): OpenWrt images and recovery research.

## Support

Made with ❤️ by mralinp. Stars and contributions are welcome.
Donations on any EVM chain: `0x6743d8fe71f18b3101f3086e8d9f8d272d0f7618`.

<img src="docs/support-qr.svg" alt="Donation address QR code" width="100">

## License

See [LICENSE](LICENSE). Bundled third-party components retain their own license terms.
