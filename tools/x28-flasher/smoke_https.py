"""Run via the frozen binary: verify its CA bundle works without the build machine's certificate paths."""
import os
import sys
from pathlib import Path

import certifi
import images

assert getattr(sys, 'frozen', False), 'run with the built binary --run-script'
assert Path(certifi.where()).is_relative_to(Path(sys._MEIPASS)), 'CA bundle is not inside the frozen app'
assert Path(certifi.where()).is_file(), 'CA bundle is missing'
os.environ['SSL_CERT_FILE'] = str(Path(sys._MEIPASS) / 'absent-ca-file')
os.environ['SSL_CERT_DIR'] = str(Path(sys._MEIPASS) / 'absent-ca-dir')
for url in ('https://github.com', 'https://raw.githubusercontent.com/mralinp/x28-flasher/main/LICENSE'):
    assert images.get(url), f'empty HTTPS response: {url}'
print('frozen HTTPS CA verification smoke test ok')
