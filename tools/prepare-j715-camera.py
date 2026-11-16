#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the pinned ISP series to a separate copy of the known 7.1.9 source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
PATCHES = REPO / 'patches-kernel/j715-camera'
ISP = Path('drivers/media/platform/apple/isp')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_base(source):
    manifest = json.loads((PATCHES / 'source-manifest.json').read_text())
    for name, hashes in manifest['files'].items():
        path = source / name
        expected = hashes['base_sha256']
        if expected is None:
            if path.exists():
                raise ValueError(f'unexpected existing source: {name}')
        elif not path.is_file() or digest(path) != expected:
            raise ValueError(f'base source hash mismatch: {name}')


def prepare(source, output):
    if os.path.lexists(output):
        raise ValueError('output must not exist')
    source = source.resolve()
    output = output.resolve()
    if output.is_relative_to(source):
        raise ValueError('output must be outside the original source')
    for tool in ('patch', 'make', 'clang', 'ld.lld'):
        if not shutil.which(tool):
            raise ValueError(f'missing dependency: {tool}')
    if not (source / '.config').is_file():
        raise ValueError('source .config is required')
    verify_base(source)
    final = json.loads((PATCHES / 't8132-source-manifest.json').read_text())
    series = (PATCHES / 'series').read_text().splitlines()
    # Validate the entire series before copying or changing a full kernel tree.
    with tempfile.TemporaryDirectory(prefix='j715-camera-series-') as tmp:
        staged = Path(tmp)
        shutil.copytree(source / ISP, staged / ISP)
        for name in series:
            with (PATCHES / name).open() as patch:
                subprocess.run(['patch', '--batch', '--forward', '-s', '-p1',
                                '-d', str(staged)], stdin=patch, check=True)
        for name, expected in final['guarded_files'].items():
            if digest(staged / name) != expected:
                raise ValueError(f'patched source hash mismatch: {name}')
        shutil.copytree(source, output, symlinks=True,
                        ignore=shutil.ignore_patterns('.git'))
        for name in final['guarded_files']:
            shutil.copy2(staged / name, output / name)
    # Preserve Rust/GPU/audio choices; only isolate the release and enable ISP.
    subprocess.run([str(output / 'scripts/config'), '--file', str(output / '.config'),
                    '--set-str', 'LOCALVERSION', '-omarchy-m4-camera-test',
                    '--disable', 'LOCALVERSION_AUTO', '--module', 'VIDEO_APPLE_ISP'],
                   check=True)
    record = {'pr421_head': final['pr421_head'],
              'input_config_sha256': digest(source / '.config'),
              'input_makefile_sha256': digest(source / 'Makefile'),
              'patch_sha256': {name: digest(PATCHES / name) for name in series},
              'privacy': 'J715 capture blocked pending verified indicator',
              'full_source_git_provenance': False}
    (output / 'camera-preparation.json').write_text(json.dumps(record, indent=2) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'BLOCKED: {exc}\n')
    print(f'Prepared isolated source: {result}')
    print('No build, module load, installation or boot changes were performed.')


if __name__ == '__main__':
    main()
