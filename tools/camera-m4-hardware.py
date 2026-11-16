#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Decode J715 ISP resources without exporting serial numbers or calibration."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys

import adt


def load_tool(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load_tool('camera_adt_audit', 'adt-audit.py')
IOREG = load_tool('camera_ioreg', 'ioreg-adt.py')


def require_j715(root):
    props = root['props']
    compatible = adt.strings(props.get('compatible', b''))
    if ('J715AP' not in compatible or
            adt.strings(props.get('model', b'')) != ['Mac16,13'] or
            adt.strings(props.get('target-type', b'')) != ['J715']):
        raise ValueError('input is not an identified J715 / Mac16,13 ADT')


def node(root, path):
    found = adt.find_path(root, path)
    if found is None:
        raise ValueError(f'missing ADT node: {path}')
    return found


def translated_regs(n, ranges):
    raw = n['props']['reg']
    if not raw or len(raw) % 16:
        raise ValueError('invalid 64-bit address/size register table')
    result = []
    for address, size in adt.regs(raw):
        physical = AUDIT.translate_adt(address, size, ranges)
        if not size or physical is None:
            raise ValueError('register window cannot be translated through arm-io ranges')
        result.append({'address': physical, 'size': size})
    return result


def decode_segments(raw):
    if not raw or len(raw) % 32:
        raise ValueError('segment-ranges must contain complete 32-byte records')
    return [dict(zip(('physical', 'virtual', 'remap', 'size', 'flags'),
                     struct.unpack_from('<QQQII', raw, off)))
            for off in range(0, len(raw), 32)]


def decode_dapf(raw):
    if not raw or len(raw) % 52:
        raise ValueError('DAPF must contain complete 52-byte records')
    result = []
    for off in range(0, len(raw), 52):
        start, end = struct.unpack_from('<QQ', raw, off)
        if start > end:
            raise ValueError('reversed DAPF window')
        result.append({'start': start, 'end': end})
    return result


def decode_instances(raw, count):
    if len(raw) != count * 16:
        raise ValueError('DART instance/register counts disagree')
    result = []
    for i in range(count):
        code, index, _, _ = struct.unpack_from('<II4s4s', raw, i * 16)
        # The numeric FourCC is little-endian, unlike the following text label.
        result.append({'type': code.to_bytes(4, 'big').decode('ascii'), 'index': index})
    return result


def driver_dapf_matches(windows, text):
    match = re.search(r'apple_isp_dapf_t8132\[\]\s*=\s*\{(.*?)\n\};', text, re.S)
    if not match:
        raise ValueError('T8132 DAPF table not found in supplied driver')
    expected = [(int(a, 16), int(b, 16)) for a, b in
                re.findall(r'\{\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+)\s*\}', match[1])]
    return bool(expected) and expected == [(w['start'], w['end']) for w in windows]


def walk_service(n):
    yield n
    for child in n['children']:
        yield from walk_service(child)


def service_facts(path, mmio):
    with path.open(errors='replace') as source:
        tree = IOREG.parse_text(source)
    if not any(n['name'] == 'J715AP' for n in walk_service(tree)):
        raise ValueError('IOService dump has no J715AP board node')
    facts = {}
    for n in walk_service(tree):
        if n['name'].startswith('isp@'):
            raw = n['props'].get('IODeviceMemory', '')
            regions = [{'address': int(a), 'size': int(b)} for a, b in
                       re.findall(r'"address"=(\d+),"length"=(\d+)', raw)]
            if regions:
                if regions != mmio:
                    raise ValueError('IOService MMIO disagrees with translated ADT')
                facts['mmio_matches_adt'] = True
        if n['name'] == 'AppleH16CamIn':
            for key in ('ISPFirmwareVersion', 'ISPFirmwareLinkDate', 'FirmwareLoaded',
                        'FrontCameraActive', 'FrontCameraStreaming'):
                value = n['props'].get(key, '')
                if re.fullmatch(r'"[A-Za-z0-9 .:_-]{1,128}"|Yes|No', value):
                    facts[key] = value.strip('"')
    return facts


def collect(root, ioservice=None, driver=None):
    require_j715(root)
    ranges = AUDIT.decode_adt_ranges(node(root, '/arm-io'))
    isp = node(root, '/arm-io/isp')
    dart = node(root, '/arm-io/dart-isp')
    regs = translated_regs(isp, ranges)
    dart_regs = translated_regs(dart, ranges)
    instance_tags = decode_instances(dart['props']['instance'], len(dart_regs))
    windows = decode_dapf(dart['props']['dapf-instance-0'])
    handles = adt.phandles(root)
    mappers = []
    for handle in adt.u32s(isp['props']['iommu-parent']):
        path, mapper = handles[handle]
        if not path.startswith('/arm-io/dart-isp/'):
            raise ValueError('ISP mapper belongs to another DART')
        sid, = adt.u32s(mapper['props']['reg'])
        mappers.append({'path': path, 'stream': sid})
    pmgr = node(root, '/arm-io/pmgr')
    psregs = AUDIT.decode_psregs(pmgr['props']['ps-regs'])
    power = []
    for d in AUDIT.decode_pmgr_devices(pmgr['props']['devices']):
        if not d.name.startswith('ISP'):
            continue
        item = {'name': d.name, 'id': d.id2, 'parents': list(d.parents),
                'flags': d.flags, 'virtual': d.virtual}
        # A virtual domain's zero offset is not a usable PMGR register.
        if not d.virtual:
            region, offset = AUDIT.pmgr_expected_offset(d, psregs)
            item.update(pmgr_reg_index=region, offset=offset)
        power.append(item)
    result = {
        'board': 'J715', 'model': 'Mac16,13',
        'isp': {'mmio': regs, 'interrupts': adt.u32s(isp['props']['interrupts']),
                'platform_type': adt.u32s(isp['props']['sensor-type'])[0],
                'power_gate_ids': adt.u32s(isp['props']['power-gates']),
                'clock_ids': adt.u32s(isp['props']['clock-ids']),
                'mappers': mappers,
                'segments': decode_segments(isp['props']['segment-ranges'])},
        'dart': {'mmio': dart_regs, 'instances': instance_tags,
                 'interrupts': adt.u32s(dart['props']['interrupts']),
                 'streams': adt.u32s(dart['props']['sid']),
                 'remapped_sources': adt.u32s(dart['props']['remap']),
                 'vm_base': struct.unpack('<Q', dart['props']['vm-base'])[0],
                 'vm_size': struct.unpack('<Q', dart['props']['vm-size'])[0],
                 'dapf': windows},
        'power_domains': power,
        'sensor_model': None,
        'indicator_verified': False,
        'eic_nodes': [p for p, _ in adt.walk(root) if re.search(r'/eic(?:/|$)', p)],
    }
    if driver:
        result['dapf_matches_upstream_t8132'] = driver_dapf_matches(windows, driver.read_text())
    if ioservice:
        result['ioservice'] = service_facts(ioservice, regs)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adt', type=Path)
    parser.add_argument('--ioservice', type=Path)
    parser.add_argument('--driver', type=Path)
    parser.add_argument('--dart-driver', type=Path)
    args = parser.parse_args()
    try:
        raw = args.adt.read_bytes()
        root, end = adt.parse(raw)
        if end != len(raw):
            raise ValueError('trailing bytes in ADT')
        result = collect(root, args.ioservice, args.driver)
        if args.dart_driver:
            result['dart_driver_has_static_remap_property'] = (
                '"apple,remap-streams"' in args.dart_driver.read_text())
    except (ValueError, OSError, KeyError, struct.error) as exc:
        parser.exit(1, f'BLOCKED: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
