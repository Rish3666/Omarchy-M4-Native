#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Kazuhide Takahashi
# Rehearse a two-phase [omarchy-m4] signing-key rotation with throwaway keys:
# phase 1 adds NEW beside OLD (signed by OLD); phase 2 re-signs everything with NEW
# and revokes OLD. Also shows why a one-step rotation (revoke OLD while the channel is
# still OLD-signed) cuts updated machines off. Same sandbox as key-rotation-trial.sh.
# Run as root on an Arch-based system with pacman, gnupg, bsdtar and repo-add:
#   sudo bash tools/key-rotation-two-phase.sh [RESULT_DIR]
# Nothing here touches the real channel, the real key or the system's pacman state.
# Two throwaway ed25519 keys (OLD, NEW) are made in a temporary GNUPGHOME; a local
# file:// repository and a "machine" (its own pacman database, cache and keyring)
# live under one temporary directory, which is deleted at the end. No network: pacman
# runs under unshare -n.
# Results go to RESULT_DIR (default ./key-rotation-result) in a new run folder.
#
set -u
[[ $(id -u) == 0 ]] || { echo 'run with sudo' >&2; exit 1; }
out="${1:-$PWD/key-rotation-result}/two-phase-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"
t=$(mktemp -d /var/tmp/key-rotation.XXXXXX)
cleanup() { for h in "$t/signer" "$t"/m/*/gnupg; do [[ -d $h ]] && gpgconf --homedir "$h" --kill all 2>/dev/null; done; rm -rf "$t"; }
trap cleanup EXIT
log() { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$out/run.log"; }
result() { printf '%-3s %-8s %s\n' "$1" "$2" "$3" | tee -a "$out/RESULTS.txt"; }
{ uname -r; pacman --version | sed -n 2p; gpg --version | head -1; pacman-key --help 2>&1 | grep -i populate; } > "$out/00-setup.txt" 2>&1

# --- keys ---------------------------------------------------------------------
export GNUPGHOME="$t/signer"; mkdir -m700 "$GNUPGHOME"
for who in OLD NEW; do
  gpg --batch --pinentry-mode loopback --passphrase '' --quick-gen-key "Rotation trial $who <trial-$who@invalid>" ed25519 sign never 2>>"$out/gpg.txt"
done
OLD=$(gpg --with-colons --list-keys trial-OLD@invalid | awk -F: '/^fpr/{print $10; exit}')
NEW=$(gpg --with-colons --list-keys trial-NEW@invalid | awk -F: '/^fpr/{print $10; exit}')
log "throwaway keys: OLD=$OLD NEW=$NEW"
sign() { # sign FILE KEY... -> FILE.sig (binary, one signature per key)
  local f=$1; shift; local args=(); for k in "$@"; do args+=(-u "$k"); done
  rm -f "$f.sig"; gpg --batch --yes --pinentry-mode loopback --passphrase '' "${args[@]}" --detach-sign -o "$f.sig" "$f" 2>>"$out/gpg.txt"
}

# --- packages (made with bsdtar; no makepkg) -----------------------------------
mkpkg() { # mkpkg NAME VER DIR-WITH-FILES -> $t/build/NAME-VER-1-any.pkg.tar.zst (pkgrel 1)
  local name=$1 ver=$2 src=$3 file="$t/build/$1-$2-1-any.pkg.tar.zst"
  mkdir -p "$t/build"
  cat > "$src/.PKGINFO" <<EOF
pkgname = $name
pkgbase = $name
pkgver = $ver-1
pkgdesc = key rotation trial package
url = https://invalid
builddate = 1
packager = trial
size = 1
arch = any
license = MIT
EOF
  (cd "$src" && bsdtar --zstd -cf "$file" .PKGINFO $(cd "$src" && find . -mindepth 1 ! -name .PKGINFO -type f | sed 's#^\./##'))
  echo "$file"
}
keyring_pkg() { # keyring_pkg VER TRUSTED-FPRS REVOKED-FPRS KEYS-TO-EXPORT...
  local ver=$1 trusted=$2 revoked=$3; shift 3
  local d="$t/src/keyring-$ver/usr/share/pacman/keyrings"; mkdir -p "$d"
  gpg --export "$@" > "$d/trial.gpg"
  : > "$d/trial-trusted"; for f in $trusted; do echo "$f:4:" >> "$d/trial-trusted"; done
  : > "$d/trial-revoked"; for f in $revoked; do echo "$f" >> "$d/trial-revoked"; done
  mkpkg trial-keyring "$ver" "$t/src/keyring-$ver"
}
payload_pkg() { # payload_pkg VER
  local d="$t/src/payload-$1/usr/share/trial"; mkdir -p "$d"; echo "payload $1" > "$d/payload"
  mkpkg trial-payload "$1" "$t/src/payload-$1"
}
# publish REPO-NAME DB-KEYS... : (re)build $t/repo/NAME with the packages in $t/stage/NAME
publish() {
  local name=$1; shift; local r="$t/repo/$name"; rm -rf "$r"; mkdir -p "$r"
  cp "$t/stage/$name"/*.pkg.tar.zst* "$r/"
  repo-add -q "$r/trial.db.tar.gz" "$r"/*.pkg.tar.zst >>"$out/repo-add.txt" 2>&1
  rm -f "$r/trial.db" "$r/trial.files"; cp "$r/trial.db.tar.gz" "$r/trial.db"
  sign "$r/trial.db" "$@"
}

# --- a "machine" ---------------------------------------------------------------
machine() { # machine NAME REPO -> config at $t/m/NAME/pacman.conf, keyring trusts OLD only
  local m="$t/m/$1"; mkdir -p "$m/root/var/lib/pacman/local" "$m/cache" "$m/gnupg"
  echo 9 > "$m/root/var/lib/pacman/local/ALPM_DB_VERSION"
  cat > "$m/pacman.conf" <<EOF
[options]
Architecture = auto
SigLevel = Required DatabaseRequired
RootDir = $m/root/
DBPath = $m/root/var/lib/pacman/
CacheDir = $m/cache/
GPGDir = $m/gnupg/
LogFile = $m/pacman.log
[trial]
Server = file://$t/repo/$2
EOF
  { pacman-key --gpgdir "$m/gnupg" --init
    gpg --armor --export "$OLD" > "$m/old.asc"
    pacman-key --gpgdir "$m/gnupg" --add "$m/old.asc"
    pacman-key --gpgdir "$m/gnupg" --lsign-key "$OLD"; } >> "$out/machine-$1.txt" 2>&1
}
repoint() { sed -i "s#^Server = .*#Server = file://$t/repo/$2#" "$t/m/$1/pacman.conf"; }
# pacman runs in a namespace with no network: it would otherwise try to look unknown keys up
# remotely (about 50 s each, and it leaves the machine). The repository is file://.
# Always -Syy: a whole run takes about a second, so repository files can share one mtime,
# and pacman would keep a stale database next to a fresh signature.
pm() { local m=$1; shift; local a=(); for x in "$@"; do case $x in -Sy) x=-Syy;; -Syu) x=-Syyu;; esac; a+=("$x"); done
  set -- "${a[@]}"; unshare -n pacman --config "$t/m/$m/pacman.conf" --noconfirm --noscriptlet "$@" >> "$out/pacman-$m.txt" 2>&1; }
# The populate step post_upgrade runs, against this machine's keyring and the
# keyring files the package installed into the machine's root.
populate() {
  local m="$t/m/$1" k="$t/m/$1/root/usr/share/pacman/keyrings"
  # Same effect as pacman-key --populate: import, lsign trusted, disable revoked.
  { pacman-key --gpgdir "$m/gnupg" --add "$k/trial.gpg"
    while IFS=: read -r f _; do [[ -n $f ]] && pacman-key --gpgdir "$m/gnupg" --lsign-key "$f"; done < "$k/trial-trusted"
    while read -r f; do [[ -n $f ]] && printf 'disable\nquit\n' | gpg --homedir "$m/gnupg" --batch --command-fd 0 --edit-key "$f"; done < "$k/trial-revoked"
  } >> "$out/machine-$1.txt" 2>&1
}
installed() { pacman --config "$t/m/$1/pacman.conf" -Q "$2" 2>/dev/null | awk '{print $2}'; }


trust() { # trust MACHINE FPR : what a setup script that knows FPR does
  local m="$t/m/$1"; gpg --armor --export "$2" > "$m/k.asc"
  { pacman-key --gpgdir "$m/gnupg" --add "$m/k.asc"; pacman-key --gpgdir "$m/gnupg" --lsign-key "$2"; } >> "$out/machine-$1.txt" 2>&1
}
stage() { # stage NAME SIGNER PKG... : copy packages, sign each with SIGNER, publish with db signed by SIGNER
  local name=$1 key=$2; shift 2; mkdir -p "$t/stage/$name"; cp "$@" "$t/stage/$name/"
  for f in "$t/stage/$name"/*.zst; do sign "$f" "$key"; done; publish "$name" "$key"
}
k1=$(keyring_pkg 1 "$OLD" "" "$OLD"); p1=$(payload_pkg 1)
k2=$(keyring_pkg 2 "$OLD $NEW" "" "$OLD" "$NEW")         # phase 1: both trusted
k3=$(keyring_pkg 3 "$NEW" "$OLD" "$OLD" "$NEW")          # phase 2: NEW trusted, OLD revoked
kx=$(keyring_pkg 9 "$NEW" "$OLD" "$OLD" "$NEW")          # one-step: the same as k3, signed by OLD
p2=$(payload_pkg 2)

# P0. baseline: every machine starts on the OLD-signed channel with keyring 1.
stage v1 "$OLD" "$k1" "$p1"
for m in updated late onestep; do machine $m v1; pm $m -Sy trial-keyring trial-payload; done
[[ $(installed updated trial-keyring) == 1-1 && $(installed late trial-keyring) == 1-1 && $(installed onestep trial-keyring) == 1-1 ]] \
  && result P0 PASS "three machines install keyring 1 from the OLD-signed channel" \
  || result P0 FAIL "baseline install failed"

# W. one-step rotation: keyring that revokes OLD, signed by OLD, while the channel stays OLD-signed.
stage vx "$OLD" "$kx" "$p1"; repoint onestep vx
if pm onestep -Syu && [[ $(installed onestep trial-keyring) == 9-1 ]]; then
  populate onestep
  pm onestep -Sy && result W FAIL "after a one-step revoke the OLD-signed channel is still accepted (unexpected)" \
    || result W PASS "one-step revoke: the updated machine now refuses the still OLD-signed channel (why two phases)"
else result W FAIL "one-step keyring did not install"; fi

# P1. phase 1: keyring 2 (OLD and NEW trusted), signed by OLD; the channel stays OLD-signed.
stage v2 "$OLD" "$k2" "$p1"; repoint updated v2
if pm updated -Syu && [[ $(installed updated trial-keyring) == 2-1 ]]; then
  populate updated
  pm updated -Sy && result P1 PASS "phase 1: keyring 2 installs; the machine trusts both and still syncs the OLD-signed channel" \
    || result P1 FAIL "phase 1: the machine refuses the OLD-signed channel after keyring 2"
else result P1 FAIL "phase 1: keyring 2 did not install"; fi

# P2. phase 2: every package and the database re-signed by NEW; keyring 3 revokes OLD.
stage v3 "$NEW" "$k3" "$p2"; repoint updated v3
if pm updated -Syu && [[ $(installed updated trial-keyring) == 3-1 && $(installed updated trial-payload) == 2-1 ]]; then
  populate updated
  result P2 PASS "phase 2: a phase-1 machine takes the NEW-signed channel and keyring 3"
else result P2 FAIL "phase 2: the phase-1 machine refused the NEW-signed channel"; fi
pm updated -Sy && result P2b PASS "phase 2: after keyring 3 the machine still syncs the NEW-signed channel" \
  || result P2b FAIL "phase 2: the NEW-signed channel is refused after keyring 3"
stage v3old "$OLD" "$k3" "$p2"; repoint updated v3old
pm updated -Sy && result P2c FAIL "an OLD-signed channel is still accepted after keyring 3" \
  || result P2c PASS "after keyring 3 an OLD-signed channel is refused"
gpg --homedir "$t/m/updated/gnupg" --with-colons --list-keys 2>/dev/null | grep -E '^pub' > "$out/P2-updated-keys.txt"

# L. a machine that skipped phase 1 (keyring 1 only) against the NEW-signed channel, then recovery.
repoint late v3
pm late -Sy && result L1 FAIL "a machine that skipped phase 1 accepted the NEW-signed channel" \
  || result L1 PASS "a machine that skipped phase 1 refuses the NEW-signed channel (needs the manual step)"
trust late "$NEW"
if pm late -Syu && [[ $(installed late trial-keyring) == 3-1 ]]; then
  populate late; pm late -Sy && result L2 PASS "after adding and lsigning NEW by hand it updates and takes keyring 3" \
    || result L2 FAIL "recovery: sync failed after keyring 3"
else result L2 FAIL "recovery by hand did not work"; fi

# F. a fresh machine connected by a setup script that knows both keys (a phase-1 kit) against phase 2.
machine fresh v3; trust fresh "$NEW"
pm fresh -Sy trial-keyring trial-payload && [[ $(installed fresh trial-payload) == 2-1 ]] \
  && result F PASS "a setup script that knows OLD and NEW connects to the NEW-signed channel" \
  || result F FAIL "a both-keys setup could not use the NEW-signed channel"

log "system: $(pacman -Q | wc -l) packages installed; trial-keyring installed on the system: $(pacman -Q trial-keyring >/dev/null 2>&1 && echo yes || echo no)"
log "done; see RESULTS.txt"
