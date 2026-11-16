#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect camera resources without opening a capture device or exposing calibration."""
import argparse
import glob
import hashlib
import json
import pathlib
import platform
import re
import subprocess

PROPERTIES = {
    'compatible', 'reg', 'reg-names', 'interrupts', 'interrupt-parent',
    'iommus', 'power-domains', 'clocks', 'clock-names', 'status',
    'memory-region', 'memory-region-names', 'AAPL,phandle',
    'dart-options', '#iommu-cells', 'cil-gpio-offset', 'cil-gpio-config',
}
MATCH = re.compile(r'isp|camera|sensor|dart|exclave|(^|/)eic', re.I)


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return {'status': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'status': None, 'error': str(exc)}


def linux_tree(root):
    root = pathlib.Path(root)
    nodes = []
    for prop in sorted(root.rglob('compatible')):
        relative = str(prop.parent.relative_to(root))
        compatible = prop.read_bytes().decode('ascii', 'replace').split('\0')
        if not MATCH.search(relative + ' ' + ' '.join(compatible)):
            continue
        nodes.append({'path': relative, 'properties': {
            p.name: p.read_bytes().hex() for p in sorted(prop.parent.iterdir())
            if p.is_file() and p.name in PROPERTIES}})
    return nodes


def apple_tree(path):
    from adt import parse, walk
    raw = pathlib.Path(path).read_bytes()
    root, end = parse(raw)
    if end != len(raw):
        raise ValueError('ADT has trailing bytes; verify input format')
    # Resource bytes retain ADT little-endian encoding. Never export calibration.
    nodes = [{'path': p, 'properties': {k: v.hex() for k, v in n['props'].items()
              if k in PROPERTIES}}
             for p, n in walk(root) if MATCH.search(p)]
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'nodes': nodes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adt', help='optional local binary Apple Device Tree')
    parser.add_argument('--dt-root', default='/sys/firmware/devicetree/base')
    args = parser.parse_args()
    root = pathlib.Path(args.dt_root)
    result = {
        'kernel': platform.release(),
        'model': (root / 'model').read_bytes().decode().rstrip('\0'),
        'compatible': (root / 'compatible').read_bytes().decode().strip('\0').split('\0'),
        'linux_nodes': linux_tree(root),
        'video_nodes': sorted(glob.glob('/dev/video*') + glob.glob('/dev/media*')),
        'setfiles': [pathlib.Path(p).name for p in sorted(glob.glob('/usr/lib/firmware/apple/isp*'))],
        'commands': {name: command(cmd) for name, cmd in {
            'isp-module': ['modinfo', 'apple-isp'],
            'v4l2': ['v4l2-ctl', '--list-devices'],
            'pipewire': ['wpctl', 'status'],
        }.items()},
    }
    if args.adt:
        result['apple_tree'] = apple_tree(args.adt)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
