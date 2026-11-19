#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the J715 test devicetree: live tree + j715-isp-additions.dtsi.

  build-j715-isp-dtb.py LIVE.dtb dts/camera-m4/t8132-j715-isp.dtsi OUT.dtb

Refuses unless LIVE.dtb is the expected tree. After building, it checks that
every node and property of the live tree is in the result unchanged, and lists
what was added.
"""
import hashlib
import struct
import subprocess
import sys
from pathlib import Path

LIVE_SHA = 'c16a7529edc4c2e5fd15552e8bf5a0d6eb1c0e7fd5b916cdad2eb6b4c223f67f'


def walk(blob):
    """Return {path: {prop: bytes}} from a flattened devicetree."""
    magic, total, off_struct, off_strings = struct.unpack_from('>4I', blob, 0)
    assert magic == 0xd00dfeed
    def string(o):
        e = blob.index(b'\0', off_strings + o)
        return blob[off_strings + o:e].decode()
    nodes, stack, p = {}, [], off_struct
    while True:
        tag, = struct.unpack_from('>I', blob, p); p += 4
        if tag == 1:  # BEGIN_NODE
            e = blob.index(b'\0', p); name = blob[p:e].decode(); p = (e + 4) & ~3
            stack.append(name)
            nodes['/' + '/'.join(s for s in stack if s)] = {}
        elif tag == 3:  # PROP
            ln, no = struct.unpack_from('>2I', blob, p); p += 8
            nodes['/' + '/'.join(s for s in stack if s)][string(no)] = blob[p:p + ln]
            p = (p + ln + 3) & ~3
        elif tag == 2:  # END_NODE
            stack.pop()
        elif tag == 4:  # NOP
            pass
        elif tag == 9:  # END
            return nodes
        else:
            raise SystemExit(f'bad FDT tag {tag}')


def main():
    live_p, add_p, out_p = map(Path, sys.argv[1:4])
    live = live_p.read_bytes()
    if hashlib.sha256(live).hexdigest() != LIVE_SHA:
        sys.exit('refused: the live tree is not c16a7529...')
    dts = subprocess.run(['dtc', '-q', '-I', 'dtb', '-O', 'dts', str(live_p)],
                         capture_output=True, text=True, check=True).stdout
    src = dts + '\n' + add_p.read_text()
    out = subprocess.run(['dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', '-', '-'],
                         input=src.encode(), capture_output=True, check=True).stdout
    a, b = walk(live), walk(out)
    changed = [(path, k) for path, props in a.items() for k, v in props.items()
               if path not in b or b[path].get(k) != v]
    if changed:
        sys.exit(f'refused: live properties changed: {changed[:10]}')
    added_nodes = sorted(set(b) - set(a))
    added_props = sorted((path, k) for path in a for k in b[path] if k not in a[path])
    out_p.write_bytes(out)
    print('live nodes', len(a), 'result nodes', len(b))
    print('added nodes', len(added_nodes))
    for n in added_nodes:
        print('  +', n)
    print('added properties on live nodes', added_props)
    print('out', out_p, len(out), hashlib.sha256(out).hexdigest())


if __name__ == '__main__':
    main()
