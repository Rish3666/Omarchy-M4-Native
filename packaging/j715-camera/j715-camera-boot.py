#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Make the J715 camera boot environment the everyday boot, and undo it.

The composed ESP boot.bin keeps this machine's boot arguments and initramfs
and replaces three parts with verified files from this directory:
  loader   stage2-ispd-m1n1.bin  (the backlight stage2 plus the ISP handoff)
  kernel   Image-dart-remap.gz   (#16 plus the DART stream remap, patch 0005)
  dtb      j715-isp-f.dtb        (the live tree plus the J715 ISP nodes)
The camera module (apple-isp.ko, j715-camera-1.0) goes to updates/.
Capture stays refused until the owner runs allow-capture.

  status | module-install | prepare | install --approved | check
  allow-capture | block-capture
  rollback (= restore) | cleanup
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path
import struct
import sys
import zlib

KIT = Path(__file__).resolve().parent
RESULT = KIT.parent / (KIT.name + '-result')
STATE = Path('/var/lib/j715-camera')
ESP_DIR = Path('/boot/efi/omarchy')
BOOT = ESP_DIR / 'boot.bin'
ESP_BACKUP = ESP_DIR / 'boot.bin.pre-camera'
CHOSEN = Path('/proc/device-tree/chosen')
BOOTARGS = b'chosen.bootargs='
GZIP = b'\x1f\x8b\x08'
INITRAMFS = b'm1n1_initramfs'
LIVE_LOADER = 'b86aee6840fe670b592271ec2816d42c5515cddc20a14e08bdc5bcbce547e6fd'
VARIANTS = {'CAMERA': 'stage2-ispd-m1n1.bin'}
LIVE_DTB = 'c16a7529edc4c2e5fd15552e8bf5a0d6eb1c0e7fd5b916cdad2eb6b4c223f67f'
TEST_DTB = 'j715-isp-f.dtb'
# Kernel with the camera series' DART remap patch (0005) only; same release, config and modules.
KERNEL_GZ = 'Image-dart-remap.gz'
MODULE = 'apple-isp.ko'
RELEASE = '7.1.9-m4-gpu-backport-20261008'
MODROOT = Path('/usr/lib/modules')
DEPS = ('videodev', 'videobuf2-common', 'videobuf2-v4l2', 'videobuf2-dma-sg', 'mc')


def fail(msg):
    sys.exit(f'j715-camera-boot: refused: {msg}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    try:
        return sha(Path(path).read_bytes())
    except PermissionError:
        fail(f'{path} is readable only by root: run with sudo')


def need_root():
    if os.geteuid() != 0:
        fail('run with sudo')


# ---- boot.bin layout (same rules as tools/m4-boot-compose.py) ----

def gzip_end(data, start):
    stream = zlib.decompressobj(31)
    try:
        stream.decompress(memoryview(data)[start:])
    except zlib.error:
        return None
    if not stream.eof:
        return None
    return len(data) - len(stream.unused_data)


def fdt_size(data, offset):
    if data[offset:offset + 4] != b'\xd0\x0d\xfe\xed' or offset + 40 > len(data):
        return None
    total, structure, strings, _, version, last = struct.unpack_from('>6I', data, offset + 4)
    if not (40 <= total <= len(data) - offset and version >= 16 and last <= 16 and
            structure < total and strings < total):
        return None
    return total


def parse_at(data, start):
    end = data.find(b'\n', start)
    if start == 0 or end < 0:
        return None
    line = data[start:end + 1]
    if not all(32 <= b < 127 for b in line[:-1]):
        return None
    kernel = end + 1
    if data[kernel:kernel + 3] != GZIP:
        return None
    dtb = gzip_end(data, kernel)
    if dtb is None:
        return None
    size = fdt_size(data, dtb)
    if size is None:
        return None
    tag = dtb + size
    if data[tag:tag + len(INITRAMFS)] != INITRAMFS or tag + len(INITRAMFS) + 4 > len(data):
        return None
    length, = struct.unpack_from('<I', data, tag + len(INITRAMFS))
    if tag + len(INITRAMFS) + 4 + length != len(data):
        return None
    return {'loader': data[:start], 'bootargs': line, 'kernel': data[kernel:dtb],
            'dtb': data[dtb:tag], 'initramfs': data[tag:]}


def parse(data):
    found, pos = [], data.find(BOOTARGS)
    while pos >= 0:
        layout = parse_at(data, pos)
        if layout is not None:
            found.append(layout)
        pos = data.find(BOOTARGS, pos + 1)
    if len(found) != 1:
        fail('boot.bin does not have exactly one loader/bootargs/kernel/dtb/initramfs layout')
    return found[0]


def summary(layout):
    return {name: {'size': len(seg), 'sha256': sha(seg)} for name, seg in layout.items()}


def newc(name, data, mode=0o100644):
    def entry(n, body, m, nlink):
        nb = n.encode() + b'\0'
        hdr = b'070701' + b''.join(b'%08X' % v for v in (
            0, m, 0, 0, nlink, 0, len(body), 0, 0, 0, 0, len(nb), 0))
        out = hdr + nb
        out += b'\0' * (-len(out) % 4)
        out += body
        out += b'\0' * (-len(out) % 4)
        return out
    return entry(name, data, mode, 1) + entry('TRAILER!!!', b'', 0, 1)




def verify_kit():
    sums = {}
    for line in (KIT / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1)
        sums[name.lstrip('*')] = digest
    for name in list(VARIANTS.values()) + [TEST_DTB, MODULE, KERNEL_GZ, 'j715-camera-boot.py']:
        if sums.get(name) != sha_file(KIT / name):
            fail(f'{name} does not match SHA256SUMS')


def write_atomic(path, data, mode=0o644):
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load_state():
    p = STATE / 'state.json'
    return json.loads(p.read_text()) if p.exists() else None


def save_result(name, obj):
    RESULT.mkdir(exist_ok=True)
    text = obj if isinstance(obj, str) else json.dumps(obj, indent=2) + '\n'
    (RESULT / name).write_text(text)
    sums = [f'{sha_file(p)}  {p.name}' for p in sorted(RESULT.iterdir())
            if p.is_file() and p.name != 'SHA256SUMS' and not p.name.startswith('._')]
    (RESULT / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')


def esp_state(st):
    cur = sha_file(BOOT)
    if st:
        if cur == st['orig_sha256']:
            return cur, 'original'
        for v, h in st['variant_sha256'].items():
            if cur == h:
                return cur, f'variant-{v}'
    return cur, 'unknown'


def mod_target():
    return MODROOT / RELEASE / 'updates' / MODULE


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127, '', f'{cmd[0]}: not found')


def cmd_module_install(_):
    need_root()
    verify_kit()
    if os.uname().release != RELEASE:
        fail(f'running {os.uname().release}, not {RELEASE}')
    data = (KIT / MODULE).read_bytes()
    target = mod_target()
    if target.exists() and sha(target.read_bytes()) != sha(data):
        fail(f'{target} exists and is not this kit\'s module')
    for d in DEPS:
        r = run(['modinfo', '-k', RELEASE, '-F', 'filename', d])
        if r.returncode or not r.stdout.strip():
            fail(f'dependency {d} is not installed for {RELEASE}')
    target.parent.mkdir(exist_ok=True)
    write_atomic(target, data, 0o644)
    r = run(['depmod', '-a', RELEASE])
    if r.returncode:
        fail(f'depmod failed: {r.stderr.strip()}')
    r = run(['modprobe', '-n', '-v', '-S', RELEASE, 'apple-isp'])
    out = {'module': str(target), 'sha256': sha(data), 'show_depends': r.stdout.strip().splitlines(),
           'installed': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    # /lib may be a symlink to usr/lib: compare the resolved paths of what modprobe would load.
    loads = [Path(w).resolve() for line in r.stdout.splitlines() for w in line.split()
             if w.endswith('.ko') or '.ko.' in w]
    if target.resolve() not in loads:
        fail(f'modprobe would not load {target}: {r.stdout.strip()} {r.stderr.strip()}')
    save_result('module-install.json', out)
    print(json.dumps(out, indent=2))
    print('the module only binds when the test devicetree hands the ISP over; capture always stays refused; arming permits only the IPC probe.')


def cmd_module_remove(_):
    need_root()
    target = mod_target()
    if target.exists():
        if sha(target.read_bytes()) != sha((KIT / MODULE).read_bytes()):
            fail(f'{target} is not this kit\'s module; left as it is')
        target.unlink()
        run(['depmod', '-a', RELEASE])
        save_result('module-remove.json', {'removed': str(target),
                    'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds')})
        print(f'removed {target} and ran depmod')
    else:
        print('the module is not installed')


def cmd_status(_):
    need_root()
    st = load_state()
    cur, which = esp_state(st)
    stage2 = (CHOSEN / 'asahi,m1n1-stage2-version')
    tools = {t: bool(run(['sh', '-c', f'command -v {t}']).stdout.strip()) for t in ('v4l2-ctl', 'ffmpeg', 'fuser')}
    print(json.dumps({'capture_tools': tools,
                      'esp_boot_sha256': cur, 'esp_boot_is': which, 'prepared': st is not None,
                      'running_stage2': stage2.read_bytes().rstrip(b'\0').decode() if stage2.exists() else None,
                      'esp_backup_present': ESP_BACKUP.exists(),
                      'module_installed': mod_target().exists(),
                      'allow_capture_conf': MODPROBE_CONF.exists(),
                      'setfiles': setfile_status()}, indent=2))


def cmd_prepare(_):
    need_root()
    verify_kit()
    orig = BOOT.read_bytes()
    st = load_state()
    if st and st['orig_sha256'] != sha(orig):
        fail('a different boot.bin was prepared before; restore/cleanup first')
    layout = parse(orig)
    if sha(layout['loader']) != LIVE_LOADER:
        fail(f'the current loader is {sha(layout["loader"])}, not the expected backlight stage2')
    if sha(layout['dtb']) != LIVE_DTB:
        fail(f'the current devicetree is {sha(layout["dtb"])}, not the expected J715 tree')
    dtb = (KIT / TEST_DTB).read_bytes()
    STATE.mkdir(mode=0o700, exist_ok=True)
    write_atomic(STATE / 'boot.bin.orig', orig, 0o600)
    variants = {}
    for v, name in VARIANTS.items():
        loader = (KIT / name).read_bytes()
        kernel = (KIT / KERNEL_GZ).read_bytes()
        new = loader + layout['bootargs'] + kernel + dtb + layout['initramfs']
        check = parse(new)
        for seg in ('bootargs', 'initramfs'):
            if check[seg] != layout[seg]:
                fail(f'variant {v}: {seg} changed')
        if check['loader'] != loader or check['dtb'] != dtb or check['kernel'] != kernel:
            fail(f'variant {v}: loader, kernel or devicetree not in place')
        write_atomic(STATE / f'boot.bin.{v}', new, 0o600)
        variants[v] = sha(new)
    st = {'orig_sha256': sha(orig), 'variant_sha256': variants, 'orig_segments': summary(layout),
          'loaders': {v: sha_file(KIT / n) for v, n in VARIANTS.items()},
          'test_dtb': sha_file(KIT / TEST_DTB),
          'kernel_gz': sha_file(KIT / KERNEL_GZ),
          'prepared': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    (STATE / 'state.json').write_text(json.dumps(st, indent=2) + '\n')
    RESULT.mkdir(exist_ok=True)
    (RESULT / 'boot.bin.orig').write_bytes(orig)
    save_result('prepare.json', st)
    print(json.dumps({'orig_sha256': st['orig_sha256'], 'variant_sha256': variants}, indent=2))
    print("prepared; the ESP is unchanged. install needs the owner's approval.")


def cmd_install(a):
    need_root()
    if not a.approved:
        fail("install needs --approved (the owner's explicit approval)")
    if a.variant not in VARIANTS:
        fail(f'unknown variant {a.variant}')
    if not mod_target().exists():
        fail('run module-install first')
    if sha_file(mod_target()) != sha_file(KIT / MODULE):
        fail('installed module differs from this kit; remove the previous kit module and run module-install first')
    st = load_state()
    if not st:
        fail('run prepare first')
    cur, which = esp_state(st)
    if which != 'original':
        fail(f'the ESP boot.bin is {which} ({cur}); restore first')
    new = (STATE / f'boot.bin.{a.variant}').read_bytes()
    orig = (STATE / 'boot.bin.orig').read_bytes()
    if sha(new) != st['variant_sha256'][a.variant] or sha(orig) != st['orig_sha256']:
        fail('the prepared files changed')
    if not ESP_BACKUP.exists() or sha_file(ESP_BACKUP) != st['orig_sha256']:
        import shutil
        if shutil.disk_usage(ESP_DIR).free < len(orig) + len(new) + (8 << 20):
            fail('not enough free space on the ESP')
        write_atomic(ESP_BACKUP, orig)
        if sha_file(ESP_BACKUP) != st['orig_sha256']:
            fail('the ESP backup copy did not verify')
    write_atomic(BOOT, new)
    if sha_file(BOOT) != st['variant_sha256'][a.variant]:
        write_atomic(BOOT, orig)
        fail('the written boot.bin did not verify; the original was put back')
    save_result(f'install-{a.variant}.json', {'variant': a.variant, 'esp_boot_sha256': sha_file(BOOT),
                'installed': datetime.datetime.now().astimezone().isoformat(timespec='seconds')})
    print('installed the camera boot environment. Reboot, then run check. '
          'Capture stays refused until allow-capture. Undo with rollback.')


def prop(name):
    p = CHOSEN / name
    return p.read_bytes() if p.exists() else None


def text(path):
    try:
        return Path(path).read_bytes().rstrip(b'\0').decode(errors='replace')
    except OSError:
        return None


def driver(dev):
    d = Path('/sys/bus/platform/devices') / dev / 'driver'
    return d.resolve().name if d.exists() else None


def cmd_check(_):
    need_root()
    dt = CHOSEN.parent
    out = {'checked': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    for name in ('asahi,m1n1-stage2-version', 'asahi,iboot2-version', 'asahi,isp-handoff'):
        out[name] = text(dt / 'chosen' / name)
    isp = dt / 'soc' / 'isp@48c000000'
    out['isp_status'] = text(isp / 'status')
    v = (isp / 'apple,platform-id').read_bytes() if (isp / 'apple,platform-id').exists() else None
    out['isp_platform_id'] = hex(struct.unpack('>I', v)[0]) if v and len(v) == 4 else None
    for d in ('iommu@48e8c0000', 'iommu@48e8e0000', 'iommu@48e900000'):
        out[f'{d}_status'] = text(dt / 'soc' / d / 'status')
    regions = {}
    for r in ('isp-firmware-text', 'isp-firmware-data', 'isp-heap'):
        node = dt / 'reserved-memory' / r
        reg = (node / 'reg').read_bytes() if (node / 'reg').exists() else b''
        ia = (node / 'iommu-addresses').read_bytes() if (node / 'iommu-addresses').exists() else b''
        w = struct.unpack('>%dI' % (len(ia) // 4), ia) if ia else ()
        regions[r] = {
            'status': text(node / 'status'),
            'reg_size': hex(struct.unpack('>2Q', reg)[1]) if len(reg) == 16 else None,  # no physical address
            'iova': hex((w[1] << 32) | w[2]) if len(w) == 5 else None,
            'iova_size': hex((w[3] << 32) | w[4]) if len(w) == 5 else None,
        }
    out['reserved_memory'] = regions
    out['drivers'] = {dev: driver(dev) for dev in ('48c000000.isp', '48e8c0000.iommu',
                                                    '48e8e0000.iommu', '48e900000.iommu')}
    out['apple_isp_loaded'] = Path('/sys/module/apple_isp').exists()
    out['kernel_version'] = os.uname().version  # DART-remap kernel: '#17 SMP PREEMPT_DYNAMIC Thu Nov 19 07:31:11 JST 2026'
    out['module_version'] = text('/sys/module/apple_isp/version')
    out['allow_capture'] = text('/sys/module/apple_isp/parameters/j715_allow_capture')  # Y / N
    out['modprobe_conf'] = MODPROBE_CONF.exists()
    out['setfiles'] = setfile_status()
    out['isp_runtime_status'] = text('/sys/bus/platform/devices/48c000000.isp/power/runtime_status')
    out['video0_users'] = run(['fuser', '/dev/video0']).stdout.split()
    out['video_devices'] = sorted(p.name for p in Path('/sys/class/video4linux').iterdir()) \
        if Path('/sys/class/video4linux').exists() else []
    out['video_names'] = {p.name: text(p / 'name') for p in Path('/sys/class/video4linux').iterdir()} \
        if Path('/sys/class/video4linux').exists() else {}
    out['media_devices'] = sorted(p.name for p in Path('/sys/bus/media/devices').iterdir()) \
        if Path('/sys/bus/media/devices').exists() else []
    k = run(['dmesg'])
    lines = [l for l in k.stdout.splitlines()
             if ('isp' in l.lower() or 'dart' in l.lower() or 'sync_state' in l)
             and 'display-crossbar' not in l and 'systemd[' not in l]
    out['dmesg_isp'] = [l for l in lines if 'reserved mem' not in l][-150:]  # no physical addresses
    out['capture_refused_lines'] = sum('camera not enabled' in l for l in lines)
    out['light_warning_lines'] = sum('camera light may stay on' in l for l in lines)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    save_result(f'check-{stamp}.json', out)
    print(json.dumps(out, indent=2))


def cmd_restore(_):
    need_root()
    st = load_state()
    if not st:
        fail('nothing was prepared')
    cur, which = esp_state(st)
    if which == 'original':
        print('the ESP boot.bin is already the original')
        return
    if not which.startswith('variant-'):
        fail(f'the ESP boot.bin is unknown ({cur}); restore by hand from boot.bin.orig')
    orig = (STATE / 'boot.bin.orig').read_bytes()
    if sha(orig) != st['orig_sha256']:
        fail('the saved original changed')
    write_atomic(BOOT, orig)
    if sha_file(BOOT) != st['orig_sha256']:
        fail('the restored boot.bin did not verify; copy boot.bin.orig by hand')
    save_result(f'restore-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.json',
                {'restored_from': which, 'esp_boot_sha256': st['orig_sha256']})
    print('restored the boot.bin from before the camera install. Reboot.')


def cmd_cleanup(a):
    need_root()
    st = load_state()
    if st:
        cur, which = esp_state(st)
        if which != 'original':
            fail(f'the ESP boot.bin is {which}; restore first')
    cmd_module_remove(a)
    if st:
        if ESP_BACKUP.exists() and sha_file(ESP_BACKUP) == st['orig_sha256']:
            ESP_BACKUP.unlink()
    for name in ['boot.bin.orig'] + [f'boot.bin.{v}' for v in VARIANTS]:
        (STATE / name).unlink(missing_ok=True)
    print(f'removed the ESP backup copy and the saved boot files; {STATE}/state.json is kept.')


MODPROBE_CONF = Path('/etc/modprobe.d/j715-camera.conf')
SETFILES = {
    'isp_2224_01XX.dat': 'dce21e48ccd35f54bad20bb2dbf043ed0842b1dadf3c5cc6cff8a2279f2aaf16',
    'isp_2226_02XX.dat': '5e2e5c4ac21df0cc0c4c90bff3807a5910cc5547a6c6995956e631d8be73b940',
}


def setfile_status():
    out = {}
    for name, digest in SETFILES.items():
        path = Path('/lib/firmware/apple') / name
        out[name] = ('ok' if path.exists() and sha(path.read_bytes()) == digest else
                     'differs' if path.exists() else 'missing')
    return out


def cmd_allow_capture(_):
    need_root()
    MODPROBE_CONF.write_text('# Owner opt-in: allow the J715 camera (j715-camera-boot.py allow-capture).\n'
                             'options apple_isp j715_allow_capture=1\n')
    os.chmod(MODPROBE_CONF, 0o644)
    print(f'wrote {MODPROBE_CONF}. Takes effect at the next boot (or after reloading apple_isp).')


def cmd_block_capture(_):
    need_root()
    MODPROBE_CONF.unlink(missing_ok=True)
    print(f'removed {MODPROBE_CONF}. Capture is refused from the next boot (or after reloading apple_isp).')


def cmd_rollback(a):
    cmd_restore(a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    sub.add_parser('module-install')
    sub.add_parser('module-remove')
    sub.add_parser('prepare')
    p = sub.add_parser('install')
    p.add_argument('--variant', choices=sorted(VARIANTS), default='CAMERA')
    p.add_argument('--approved', action='store_true')
    sub.add_parser('check')
    sub.add_parser('restore')
    sub.add_parser('rollback')
    sub.add_parser('allow-capture')
    sub.add_parser('block-capture')
    sub.add_parser('cleanup')
    a = ap.parse_args()
    globals()['cmd_' + a.cmd.replace('-', '_')](a)


if __name__ == '__main__':
    main()
