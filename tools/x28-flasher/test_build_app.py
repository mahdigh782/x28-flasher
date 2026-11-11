"""App layout/signing regression tests; no macOS tools needed for these mocks."""
import json
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_app


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / 'x28-flasher'
        (self.src / '_internal/example.dist-info').mkdir(parents=True)
        (self.src / '_internal/identity.json').write_text(json.dumps({'version': '0.2.1'}))
        (self.src / 'x28-flasher').write_bytes(b'backend')

    def test_backend_stays_onedir_in_resources_and_finished_app_is_signed_and_verified(self):
        with patch.object(sys, 'argv', ['build_app.py', '--dist', str(self.root)]), \
             patch.object(build_app.shutil, 'which', return_value='/usr/bin/swiftc'), \
             patch.object(build_app.subprocess, 'run') as run:
            build_app.main()
        app = self.root / 'X28 Flasher.app'
        self.assertEqual((app / 'Contents/Resources/backend/x28-flasher').read_bytes(), b'backend')
        self.assertTrue((app / 'Contents/Resources/backend/_internal/example.dist-info').is_dir())
        self.assertFalse((app / 'Contents/Frameworks').exists())
        info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
        self.assertEqual(info['CFBundleExecutable'], 'X28 Flasher')
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[-2:], [['codesign', '--force', '--sign', '-', str(app)],
                                         ['codesign', '--verify', '--deep', '--strict', str(app)]])

    def test_missing_swift_does_not_replace_an_existing_app(self):
        app = self.root / 'X28 Flasher.app'
        app.mkdir()
        marker = app / 'keep'
        marker.write_text('old build')
        with patch.object(sys, 'argv', ['build_app.py', '--dist', str(self.root)]), \
             patch.object(build_app.shutil, 'which', return_value=None), self.assertRaisesRegex(SystemExit, 'swiftc'):
            build_app.main()
        self.assertEqual(marker.read_text(), 'old build')


if __name__ == '__main__':
    unittest.main()
