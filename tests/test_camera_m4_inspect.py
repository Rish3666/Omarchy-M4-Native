# SPDX-License-Identifier: MIT
"""Resource collection must retain hardware data and omit private calibration."""
import importlib.util
import pathlib
import struct
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('camera_inspect', TOOLS / 'camera-m4-inspect.py')
inspect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspect)


def node(props, children=()):
    result = struct.pack('<II', len(props), len(children))
    for key, value in props.items():
        result += key.encode().ljust(32, b'\0') + struct.pack('<I', len(value))
        result += value + bytes(-len(value) % 4)
    return result + b''.join(children)


class CameraInspectTests(unittest.TestCase):
    def test_linux_resource_encoding_and_privacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            isp = pathlib.Path(tmp) / 'soc' / 'isp@1234'
            isp.mkdir(parents=True)
            (isp / 'compatible').write_bytes(b'apple,t8132-isp\0')
            reg = struct.pack('>IIII', 4, 0x1234, 0, 0x4000)
            (isp / 'reg').write_bytes(reg)
            (isp / 'calibration').write_bytes(b'private')
            result = inspect.linux_tree(tmp)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['properties']['reg'], reg.hex())
            self.assertNotIn('calibration', result[0]['properties'])

    def test_adt_does_not_export_calibration(self):
        data = node({'name': b'device-tree\0', 'model': b'J715AP\0',
                     'serial-number': b'private'}, [node({
            'name': b'isp\0', 'reg': struct.pack('<QQ', 0x1234, 0x4000),
            'segment-ranges': bytes(32),
            'calibration': b'private', 'serial-number': b'private',
        })])
        with tempfile.NamedTemporaryFile() as f:
            f.write(data)
            f.flush()
            result = inspect.apple_tree(f.name)
        self.assertEqual(result['nodes'][0]['path'], '/isp')
        self.assertEqual(set(result['nodes'][0]['properties']), {'reg', 'segment-ranges'})
        self.assertEqual(result['identity'], {'model': b'J715AP\0'.hex()})
        self.assertEqual(len(result['sha256']), 64)

    def test_adt_rejects_trailing_data(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(node({'name': b'device-tree\0'}) + b'trailing')
            f.flush()
            with self.assertRaises(ValueError):
                inspect.apple_tree(f.name)


if __name__ == '__main__':
    unittest.main()
