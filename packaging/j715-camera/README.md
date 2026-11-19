# J715 camera boot environment (local, owner-run)

`j715-camera-boot.py` makes the J715 camera boot environment this machine's
everyday boot and undoes it. The J715 tester build is outside
`omarchy-m4-update`, so this is an owner-run local step, not a channel
package. It keeps the owner's boot arguments and initramfs and replaces the
stage2, kernel and devicetree of the ESP `boot.bin`, keeping the previous
`boot.bin` for `rollback`.

Place these build artifacts next to the script (hashes in `ARTIFACTS.sha256`),
then write `SHA256SUMS` for them, the script and a README:

| File | Source |
|---|---|
| `stage2-ispd-m1n1.bin` | `patches-m1n1/j715-isp-handoff` (reproducible) |
| `Image-dart-remap.gz` | the owner's #16 tree plus `patches-kernel/j715-camera/0005` (incremental build, same release and symvers), `gzip -9 -n` |
| `j715-isp-f.dtb` | `tools/build-j715-isp-dtb.py` with `dts/camera-m4/t8132-j715-isp.dtsi` |
| `apple-isp.ko` | the ISP driver after `patches-kernel/j715-camera/series` (0001-0006), built out of tree for `7.1.9-m4-gpu-backport-20261008` |

The IMX958 setfiles come from the owner's macOS with
`tools/extract-imx958-setfile.py` and go to `/lib/firmware/apple`; they are
Apple calibration data for that Mac and are not distributed.

Commands: `status`, `module-install`, `prepare`, `install --approved`,
`check`, `allow-capture` / `block-capture` (owner opt-in through
`/etc/modprobe.d/j715-camera.conf`), `rollback`, `cleanup`.

If the camera light stays on after a failed stream, hold the power button
until the startup options appear; rebooting, powering off or unplugging does
not clear it.
