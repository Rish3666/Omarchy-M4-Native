# J715 ISP handoff for the backlight stage2

`0001-stage2-isp-handoff.patch` ports `dt_display_transaction` (as
`dt_isp_transaction`), `dt_set_j713_isp_one` and `dt_set_j713_isp` from
aurora-silicon/aura `e0a116b1d3f3e3ecce1a4987f9fd5ce5babffdf2`
(GPL-2.0-only) into `src/kboot.c` of the backlight stage2 and adds J715.
The patched `kboot.c` is MIT AND GPL-2.0-only. At boot it fills the ISP
firmware placeholders of `dts/camera-m4/t8132-j715-isp.dtsi` from this boot's
ADT, sets `apple,platform-id` from the ADT sensor type, enables the ISP and its
DARTs and records `asahi,isp-handoff = "handed-over"` in `/chosen`.

Inputs (apply with `patch -p1` to `src/kboot.c`):

- stage2 source archive `m1n1-stage2-source.tar.gz`, SHA-256
  `c394517941a5700b227718bb02e3df3dd43c9ad5a8e53c9447a55d3c36846c44`
- `display/j713/m1n1-base/src/{kboot.c,dart.c,dart.h}` of this repository
  (`kboot.c` 33f699e5…)

`build-stage2.sh` builds stock, backlight and ISP-handoff stage2 in the
`m4-gravity-builder:20261008-rebuilt` container (`/in`, `/out`). On
2026-11-19 it reproduced all three byte for byte:

| stage2 | SHA-256 |
|---|---|
| stock | `3a3f7a64c65fc366d5ac9aece3e1bee64119be012aa1ec5b15d2743c6f91fce4` |
| backlight | `b86aee6840fe670b592271ec2816d42c5515cddc20a14e08bdc5bcbce547e6fd` |
| ISP handoff | `5a9b1a648c7ae8ed6c379425848cb174d6ab26722866b471a599caab064a913c` |

Cargo fetches the stage2's git dependencies, so the container needs network
access.
