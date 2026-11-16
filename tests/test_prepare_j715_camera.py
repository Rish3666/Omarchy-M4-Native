# SPDX-License-Identifier: MIT
"""The camera preparation path must reject unsafe or mismatched input."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
spec = importlib.util.spec_from_file_location('prepare_camera', TOOLS / 'prepare-j715-camera.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PrepareCameraTests(unittest.TestCase):
    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sentinel = root / 'known-good'
            sentinel.write_text('preserve me')
            with self.assertRaisesRegex(ValueError, 'must not exist'):
                prepare.prepare(root / 'source', root)
            self.assertEqual(sentinel.read_text(), 'preserve me')

    def test_output_inside_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'outside'):
                prepare.prepare(root, root / 'recursive-copy')
            self.assertFalse((root / 'recursive-copy').exists())

    def test_modified_base_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'isp.c').write_bytes(b'local edits')
            manifest = {'files': {'isp.c': {
                'base_sha256': hashlib.sha256(b'expected upstream').hexdigest()}}}
            (root / 'source-manifest.json').write_text(json.dumps(manifest))
            with patch.object(prepare, 'PATCHES', root):
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    prepare.verify_base(source)
            self.assertEqual((source / 'isp.c').read_bytes(), b'local edits')

    def test_modified_supporting_driver_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'dart.c').write_bytes(b'local DART changes')
            (root / 'source-manifest.json').write_text(json.dumps({'files': {}}))
            manifest = {'supporting_base_sha256': {
                'dart.c': hashlib.sha256(b'pinned DART source').hexdigest()}}
            (root / 't8132-source-manifest.json').write_text(json.dumps(manifest))
            with patch.object(prepare, 'PATCHES', root):
                with self.assertRaisesRegex(ValueError, 'supporting source hash mismatch'):
                    prepare.verify_base(source)
            self.assertEqual((source / 'dart.c').read_bytes(), b'local DART changes')


if __name__ == '__main__':
    unittest.main()
