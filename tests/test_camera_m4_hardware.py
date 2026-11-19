# SPDX-License-Identifier: MIT
"""Test byte order, address translation and rejection of incomplete ISP data."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('camera_hardware', TOOLS / 'camera-m4-hardware.py')
hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hardware)


class HardwareTests(unittest.TestCase):
    def test_wrong_air_size_is_rejected(self):
        root = {'props': {'compatible': b'J713AP\0Mac16,12\0AppleARM\0',
                          'model': b'Mac16,12\0', 'target-type': b'J713\0'}}
        with self.assertRaisesRegex(ValueError, 'not an identified J715'):
            hardware.require_j715(root)

    def test_mmio_requires_parent_translation(self):
        n = {'props': {'reg': struct.pack('<QQ', 0x28c000000, 0x3ff0000)}}
        ranges = [(0, 0x200000000, 0x3a0000000)]
        self.assertEqual(hardware.translated_regs(n, ranges),
                         [{'address': 0x48c000000, 'size': 0x3ff0000}])
        with self.assertRaisesRegex(ValueError, 'cannot be translated'):
            hardware.translated_regs(n, [(0, 0x200000000, 0x1000)])

    def test_segment_size_is_u32_and_flags_are_separate(self):
        data = struct.pack('<QQQII', 0x10000d78000, 0, 0x10000000000, 0xcd0000, 1)
        result, = hardware.decode_segments(data)
        self.assertEqual(result['size'], 0xcd0000)
        self.assertEqual(result['flags'], 1)
        self.assertEqual(result['physical'], 0x10000d78000)
        with self.assertRaisesRegex(ValueError, '32-byte'):
            hardware.decode_segments(data[:-1])

    def test_dapf_end_is_not_treated_as_size(self):
        data = struct.pack('<QQ9I', 0x380704000, 0x380704063, *([0] * 9))
        result = hardware.decode_dapf(data)
        self.assertEqual(result, [{'start': 0x380704000, 'end': 0x380704063}])
        with self.assertRaisesRegex(ValueError, '52-byte'):
            hardware.decode_dapf(data + b'X')

    def test_driver_dapf_drift_is_detected(self):
        text = 'static const struct isp_dapf_window apple_isp_dapf_t8132[] = {\n { 0x100, 0x1ff },\n};'
        self.assertTrue(hardware.driver_dapf_matches([{'start': 0x100, 'end': 0x1ff}], text))
        self.assertFalse(hardware.driver_dapf_matches([{'start': 0x100, 'end': 0x200}], text))

    def test_instance_fourcc_has_numeric_byte_order(self):
        raw = b'TRAD' + struct.pack('<I', 0) + b'DARTTLL\0'
        self.assertEqual(hardware.decode_instances(raw, 1), [{'type': 'DART', 'index': 0}])
        raw = b'FPAD' + struct.pack('<I', 0) + b'DAPFTLL\0'
        self.assertEqual(hardware.decode_instances(raw, 1), [{'type': 'DAPF', 'index': 0}])

    def test_service_facts_omit_serial_and_calibration(self):
        text = '''+-o J715AP  <class IOPlatformExpertDevice>
  +-o AppleH16CamIn  <class AppleH16CamIn>
      "ISPFirmwareVersion" = "6.105"
      "FrontCameraModuleSerialNumString" = "private"
      "calibration" = <01020304>
      "FrontCameraStreaming" = No
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'service.txt'
            path.write_text(text)
            facts = hardware.service_facts(path, [])
        self.assertEqual(facts, {'ISPFirmwareVersion': '6.105', 'FrontCameraStreaming': 'No'})

    def test_sensor_requires_consistent_independent_log_fields(self):
        text = 'PipelineFrequencyRequest, sensorID=0x958, cfgNum=6, fps=30\nIMX958 boot flag 0x0\n'
        facts = hardware.log_facts(text)
        self.assertEqual(facts['confirmed_sensor_model'], 'IMX958')
        self.assertEqual(facts['modes'], [{'sensor_id': 0x958, 'config_index': 6, 'requested_fps': 30}])
        self.assertIsNone(hardware.log_facts('IMX958 boot flag 0')['confirmed_sensor_model'])
        self.assertIsNone(hardware.log_facts(text + 'sensorID=0x558')['confirmed_sensor_model'])

    def test_streaming_and_geometry_do_not_prove_indicator_or_setfile(self):
        text = ('SensorRaw:3040x5760, SensorCrop:3040x2880\n'
                'UpdateSensorStateInIORegForChannel - channel: 0, name: Streaming, state: 1\n'
                'UpdateSensorStateInIORegForChannel - channel: 0, name: Streaming, state: 0\n'
                'FrontCameraModuleSerialNumString=private-secret\n')
        facts = hardware.log_facts(text)
        self.assertEqual(facts['streaming_state_sequence'], [1, 0])
        self.assertEqual(facts['pipeline_shapes'], [{'raw': [3040, 5760], 'processed': [3040, 2880]}])
        self.assertFalse(facts['indicator_mechanism_confirmed'])
        self.assertFalse(facts['setfile_module_revision_confirmed'])
        self.assertNotIn('private-secret', str(facts))


if __name__ == '__main__':
    unittest.main()
