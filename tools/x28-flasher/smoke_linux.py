"""Run under dbus-run-session + xvfb-run after installing the .deb; no modem is touched."""
import os
import subprocess
from pathlib import Path

native = Path('/opt/x28-flasher/x28-flasher-window')
assert native.is_file()
# The native launcher must not replace or break the terminal commands.
subprocess.run(['/usr/bin/x28-flasher', '--selftest'], check=True, timeout=30)
log = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'x28-flasher/native.log'
before = log.stat().st_size if log.exists() else 0
try:
    result = subprocess.run([str(native), '--selftest'], timeout=90)
    assert result.returncode == 0, f'native self-test exited {result.returncode}'
    assert b'native window selftest ok' in log.read_bytes()[before:]
    assert not (Path.home() / '.x28-flasher/running.json').exists(), 'native window left its backend running'
except BaseException:
    if log.exists():
        print(log.read_text(encoding='utf-8', errors='replace'))
    raise
print('installed Linux native window smoke test ok')
