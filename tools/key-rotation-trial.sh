#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Kazuhide Takahashi
# Rehearse the [omarchy-m4] signing-key rotation with throwaway keys.
# Run as root on an Arch-based system with pacman, gnupg, bsdtar and repo-add:
#   sudo bash tools/key-rotation-trial.sh [RESULT_DIR]
# Nothing here touches the real channel, the real key or the system's pacman state.
# Two throwaway ed25519 keys (OLD, NEW) are made in a temporary GNUPGHOME; a local
# file:// repository and a "machine" (its own pacman database, cache and keyring)
# live under one temporary directory, which is deleted at the end. No network: pacman
# runs under unshare -n.
# Results go to RESULT_DIR (default ./key-rotation-result) in a new run folder.
#
# Questions it answers:
#  A. Baseline: a machine that trusts OLD (as m4-channel-setup.py does) installs
#     from a repository signed by OLD.
#  B. A database signed by both OLD and NEW (one .sig with two signatures): a machine
#     that knows only OLD refuses it, so dual signing is no transition window.
#  C. The documented rotation: a keyring package that adds NEW as trusted and lists
#     OLD as revoked, signed by OLD, then populated (scriptlets are skipped in a
#     separate root, so the populate step is run the way post_upgrade does it).
#  D. After C: a NEW-signed database and package install; an OLD-signed one is refused.
#  E. A machine that never updated (knows only OLD) against the NEW-signed repository:
#     refused, which is what published kits and not-yet-updated machines would see.
set -u
[[ $(id -u) == 0 ]] || { echo 'run with sudo' >&2; exit 1; }
out="${1:-$PWD/key-rotation-result}/run-$(date +%Y%m%d-%H%M%S)"
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

# A. baseline: repository v1 signed by OLD
k1=$(keyring_pkg 1 "$OLD" "" "$OLD"); p1=$(payload_pkg 1)
mkdir -p "$t/stage/v1"; cp "$k1" "$p1" "$t/stage/v1/"; for f in "$t/stage/v1"/*.zst; do sign "$f" "$OLD"; done
publish v1 "$OLD"
machine updated v1; machine never v1
pm updated -Sy trial-keyring trial-payload && [[ $(installed updated trial-payload) == 1-1 ]] \
  && result A PASS "machine trusting OLD installs from an OLD-signed repository" \
  || result A FAIL "baseline install failed (pacman-updated.txt)"
pm never -Sy trial-payload || true

# B. database signed by OLD and NEW together; machine knows only OLD
mkdir -p "$t/stage/v1b"; cp "$t/stage/v1"/* "$t/stage/v1b/"; publish v1b "$OLD" "$NEW"
gpg --list-packets "$t/repo/v1b/trial.db.sig" 2>/dev/null | grep -c ':signature packet' > "$out/B-signature-count.txt"
repoint never v1b
# docs/package-channel.md relies on this refusal: dual signing cannot bridge a rotation.
if pm never -Sy; then result B FAIL "an OLD+NEW double-signed database is accepted by a machine that knows only OLD"
else result B PASS "an OLD+NEW double-signed database is refused by a machine that knows only OLD (no dual-signing window)"; fi

# C. rotation release v2: keyring 2 (NEW trusted, OLD revoked, both exported), signed by OLD
k2=$(keyring_pkg 2 "$NEW" "$OLD" "$OLD" "$NEW")
mkdir -p "$t/stage/v2"; cp "$k2" "$p1" "$t/stage/v2/"; for f in "$t/stage/v2"/*.zst; do sign "$f" "$OLD"; done
publish v2 "$OLD"
repoint updated v2
if pm updated -Syu && [[ $(installed updated trial-keyring) == 2-1 ]]; then
  populate updated
  result C PASS "keyring 2 (signed by OLD) installs; populate adds NEW and revokes OLD"
else result C FAIL "keyring 2 did not install (pacman-updated.txt)"; fi
gpg --homedir "$t/m/updated/gnupg" --with-colons --list-keys 2>/dev/null | grep -E '^pub' > "$out/C-updated-keys.txt"

# D. repository v3 signed by NEW only
p2=$(payload_pkg 2)
mkdir -p "$t/stage/v3"; cp "$k2" "$p2" "$t/stage/v3/"; for f in "$t/stage/v3"/*.zst; do sign "$f" "$NEW"; done
publish v3 "$NEW"
repoint updated v3
pm updated -Syu && [[ $(installed updated trial-payload) == 2-1 ]] \
  && result D1 PASS "after the rotation, a NEW-signed database and package install" \
  || result D1 FAIL "the NEW-signed repository was refused after the rotation"
mkdir -p "$t/stage/v3old"; cp "$t/stage/v3"/*.zst "$t/stage/v3old/"; for f in "$t/stage/v3old"/*.zst; do sign "$f" "$OLD"; done
publish v3old "$OLD"; repoint updated v3old
pm updated -Sy && result D2 FAIL "an OLD-signed database is still accepted after OLD was revoked" \
  || result D2 PASS "an OLD-signed database is refused after the rotation"

# E. a machine that never took keyring 2, against the NEW-signed repository
repoint never v3
pm never -Sy && result E FAIL "a machine that knows only OLD accepted the NEW-signed repository" \
  || result E PASS "a machine that knows only OLD refuses the NEW-signed repository (expected; needs a migration path)"

log "system: $(pacman -Q | wc -l) packages installed; trial-keyring installed on the system: $(pacman -Q trial-keyring >/dev/null 2>&1 && echo yes || echo no)"
log "done; see RESULTS.txt"
