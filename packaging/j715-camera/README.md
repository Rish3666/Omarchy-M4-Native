# J715 camera boot environment (local, owner-run)

`j715-camera-boot.py` makes the J715 camera boot environment this machine's
everyday boot and undoes it. The J715 tester build is outside
`omarchy-m4-update`, so this is an owner-run local step, not a channel
package. It keeps the owner's boot arguments and initramfs and replaces the
stage2, kernel and devicetree of the ESP `boot.bin`, keeping the previous
`boot.bin` for `rollback`.

Place these build artifacts and `ARTIFACTS.sha256` next to the script, then
write `SHA256SUMS` for the artifacts, the script and a README. The script
refuses any artifact that does not match both: `ARTIFACTS.sha256` pins the
tested build.

| File | Source |
|---|---|
| `stage2-ispd-m1n1.bin` | `patches-m1n1/j715-isp-handoff` (reproducible) |
| `Image-dart-remap.gz` | the owner's #16 tree plus `patches-kernel/j715-camera/0005` (incremental build, same release and symvers), `gzip -9 -n` |
| `j715-isp-f.dtb` | `tools/build-j715-isp-dtb.py` with `dts/camera-m4/t8132-j715-isp.dtsi` |
| `apple-isp.ko` | the ISP driver after `patches-kernel/j715-camera/series` (0001-0006), built out of tree for `7.1.9-m4-gpu-backport-20261008` |

All four keep the installed release `7.1.9-m4-gpu-backport-20261008`.
`tools/prepare-j715-camera.py` and `tools/build-j715-camera.sh` build a
separate `7.1.9-omarchy-m4-camera-test` release for offline and KUnit tests;
their output is not installable with this script.

The IMX958 setfiles come from the owner's macOS with
`tools/extract-imx958-setfile.py` and go to `/lib/firmware/apple`; they are
Apple calibration data for that Mac and are not distributed.

Commands: `status`, `module-install` / `module-remove`, `prepare`,
`install --approved`, `check`, `allow-capture` / `block-capture` (owner opt-in
through `/etc/modprobe.d/j715-camera.conf`), `rollback`, `cleanup`.
To replace the module of an earlier kit, run `module-remove`, then
`module-install`; the new module is used from the next boot.

`prepare` keeps the whole original `boot.bin` (this Mac's boot arguments and
Apple firmware) as `boot.bin.orig`, root-only, in the result folder. It is
left out of the result's `SHA256SUMS`; do not share it.

If the camera light stays on after a failed stream, hold the power button
until the startup options appear; rebooting, powering off or unplugging does
not clear it.
