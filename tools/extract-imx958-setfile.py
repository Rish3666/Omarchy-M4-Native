#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extract the IMX958 ISP setfiles from this Mac's camera daemon. Read-only.

Run on the J715's own macOS (no sudo needed):
  python3 extract-imx958-setfile.py [--daemon PATH] [--out DIR]

Same method as the Gravity/Asahi installer (gravity_firmware/isp.py) and
omarchy-mac-installer PR #208: scan the daemon binary at 4 KiB boundaries for
a setfile header whose magic is a known IMX958 setfile, and save it as
apple/isp_<name>.dat. Nothing on the Mac is modified. The setfiles are
Apple's calibration data for this machine's camera: keep them private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

ALIGN = 0x1000
# magic -> (name, size), from PR #208 / the Linux driver's setfile table
IMX958 = {0x22240106: ('2224_01XX', 0x6ff4), 0x22260201: ('2226_02XX', 0x6ff4)}
CANDIDATES = ['/usr/libexec/appleh16camerad',
              '/System/Library/PrivateFrameworks/AppleH16CameraInterface.framework/Resources/appleh16camerad',
              '/System/Library/PrivateFrameworks/AppleH16CameraInterface.framework/Versions/A/Resources/appleh16camerad']


def header_ok(h):
    return (h[2] == 0 and h[3] == 0 and h[4] and (h[4] & 0xff000000) == h[4] and
            h[5] and (h[5] & 0xffff0000) == h[5] and h[6] == 0 and h[7] == 0x3c00000)


def find_daemon():
    for p in CANDIDATES:
        if os.path.isfile(p):
            return p
    for root in ('/usr/libexec', '/System/Library/PrivateFrameworks'):
        for dirpath, _, files in os.walk(root):
            if 'appleh16camerad' in files:
                return os.path.join(dirpath, 'appleh16camerad')
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--daemon')
    ap.add_argument('--out', type=Path, default=Path('j715-imx958-setfiles'))
    a = ap.parse_args()
    daemon = a.daemon or find_daemon()
    if not daemon:
        sys.exit('appleh16camerad not found; pass --daemon PATH')
    data = Path(daemon).read_bytes()
    print(f'daemon: {daemon} ({len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()})')
    a.out.mkdir(parents=True, exist_ok=True)
    os.chmod(a.out, 0o700)
    found, all_magics = [], []
    for off in range(0, len(data) - 32, ALIGN):
        h = struct.unpack('>8L', data[off:off + 32])
        if not header_ok(h):
            continue
        all_magics.append(f'{h[0]:#010x}@{off:#x}')
        if h[0] not in IMX958:
            continue
        name, size = IMX958[h[0]]
        blob = data[off:off + ((size + 63) & ~63)]
        path = a.out / f'isp_{name}.dat'
        path.write_bytes(blob)
        os.chmod(path, 0o600)
        found.append({'file': path.name, 'magic': f'{h[0]:#010x}', 'offset': hex(off),
                      'size': hex(len(blob)), 'sha256': hashlib.sha256(blob).hexdigest()})
        print(f'found {path.name} at {off:#x}')
    report = {'daemon': daemon, 'daemon_sha256': hashlib.sha256(data).hexdigest(),
              'imx958': found, 'all_setfile_magics': all_magics}
    (a.out / 'extract.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['imx958'], indent=2))
    if not found:
        sys.exit(f'no IMX958 setfile found ({len(all_magics)} setfile headers seen); see extract.json')


if __name__ == '__main__':
    main()
