"""Exact backup-rootfs writes: synthetic vendor bytes and a fake DA, never real hardware."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import slot_entry as entry
import slot_session as session


class BackupRootfsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.parts = {}
        for name, addr, data in (
            ('rootfs_a', 0x13600000, b'VENDOR_A' * (0x4000000 // 8)),
            ('rootfs_b', 0x1fc00000, b'VENDOR_B' * (0x4000000 // 8)),
            ('proinfo', 0x600000, b'this-unit'), ('misc', 0x700000, b'boot-selection'), ('boot_para', 0x8e00000, b'boot-params')):
            path = self.root / name
            path.write_bytes(data)
            self.parts[name] = {'image': str(path), 'sha256': session.digest(data), 'offset': addr, 'size': len(data)}
        self.addCleanup(patch.stopall)
        patch.object(entry, 'verified_backup', return_value=([], self.parts)).start()
        patch.object(entry, 'host_identity', return_value='host').start()
        patch.object(entry, 'slot_tools_digest', return_value='tools').start()

    def load(self, source='b', target='rootfs_b', **kwargs):
        return entry.load_inputs(self.root, self.root / 'loader', target, kwargs.pop('mode', 'write'),
                                 kwargs.pop('candidate_dir', None), backup_rootfs=source, **kwargs)

    def test_each_source_can_be_written_to_either_fixed_slot_including_itself(self):
        for source in ('a', 'b'):
            for target in ('rootfs_a', 'rootfs_b'):
                with self.subTest(source=source, target=target):
                    _, _, original, candidate, spec, identity, base = self.load(source, target)
                    self.assertEqual(session.digest(candidate), self.parts['rootfs_' + source]['sha256'])
                    self.assertEqual(spec.addr, self.parts[target]['offset'])
                    self.assertEqual(spec.original_sha, self.parts[target]['sha256'])
                    self.assertEqual(identity['unit'], self.parts['proinfo']['sha256'])
                    self.assertEqual(identity['backup_rootfs'], source)
                    self.assertIsNone(base)
                    spec.validate(original, candidate)  # source==target is explicitly allowed
                    with self.assertRaises(ValueError):
                        spec.validate(original, candidate[:-1])
                    with self.assertRaises(ValueError):
                        spec.validate(original, b'X' + candidate[1:])

    def test_tampered_backup_source_is_rejected_before_a_session(self):
        with Path(self.parts['rootfs_b']['image']).open('r+b') as stream:
            stream.write(b'changed!')
        with self.assertRaisesRegex(ValueError, 'verified source'):
            self.load()

    def test_offline_entry_accepts_backup_source_without_a_candidate_manifest(self):
        loader = self.root / 'loader'
        loader.write_bytes(b'da')
        argv = ['slot_entry.py', 'rootfs_a', 'write', '--backup', str(self.root), '--loader', str(loader),
                '--backup-rootfs', 'b', '--no-ssh', '--no-uart']
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), patch.object(entry, 'open_da', side_effect=AssertionError('USB forbidden')), \
             contextlib.redirect_stdout(output):
            entry.main()
        self.assertIn('Source: verified backup rootfs_b', output.getvalue())
        self.assertIn('OFFLINE DRY RUN', output.getvalue())

    def test_conflicting_or_non_rootfs_inputs_are_rejected(self):
        for args in ({'source': 'c'}, {'target': 'misc'}, {'mode': 'restore'},
                     {'candidate_dir': self.root}, {'base_dir': self.root}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.load(**args)

    def test_restoring_own_backup_over_changed_live_data_writes_and_reads_only_target(self):
        _, _, original, candidate, spec, _, _ = self.load()
        class FakeDA:
            data = b'changed-live-data'
            calls = []
            def writeflash(da, addr, length, filename, **kwargs):
                da.calls.append(('write', addr, length))
                da.data = Path(filename).read_bytes()
                return True
            def readflash(da, addr, length, filename, **kwargs):
                da.calls.append(('read', addr, length))
                Path(filename).write_bytes(da.data)
                return True
        da = FakeDA()
        out = session.run_session(da, spec, original, candidate, self.root, mode='write', guards=False)
        self.assertEqual(session.digest(da.data), spec.candidate_sha)
        self.assertEqual(da.calls, [('write', spec.addr, spec.size), ('read', spec.addr, spec.size)])
        events = [json.loads(line) for line in (out / 'journal.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1], {'status': 'TARGET_VERIFIED'})
        self.assertEqual(entry.phrase(spec, 'write', spec.candidate_sha, False, backup_rootfs='b'),
                         f'WRITE write rootfs_b {spec.candidate_sha[:12]} FROM-BACKUP-rootfs_b')


if __name__ == '__main__':
    unittest.main()
