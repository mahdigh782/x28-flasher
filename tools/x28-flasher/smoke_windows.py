"""Install the actual Windows package and check that its native window loads and shuts down."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if os.name != 'nt':
    raise SystemExit('Windows only')
installer = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as folder:
    app = Path(folder) / 'X28 Flasher'
    install_log = Path(folder) / 'install.log'
    log = Path(os.environ['LOCALAPPDATA']) / 'X28 Flasher/native.log'
    try:
        subprocess.run([str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                        f'/DIR={app}', f'/LOG={install_log}'], timeout=300, check=True)
        assert (app / 'X28 Flasher.exe').is_file()
        before = log.stat().st_size if log.exists() else 0
        result = subprocess.run([str(app / 'X28 Flasher.exe'), '--selftest'], timeout=90)
        assert result.returncode == 0, f'native self-test exited {result.returncode}'
        assert b'native window selftest ok' in log.read_bytes()[before:]
        # A successful window close must leave no running backend behind.
        run_file = Path.home() / '.x28-flasher/running.json'
        assert not run_file.exists(), 'native window left its backend running'
    except BaseException:
        for path in (install_log, log):
            if path.exists():
                print(path.read_text(encoding='utf-8', errors='replace'))
        raise
print('installed Windows native window smoke test ok')
