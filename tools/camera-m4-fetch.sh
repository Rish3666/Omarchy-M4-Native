#!/bin/bash
# SPDX-License-Identifier: MIT
# Fetch into an isolated bare repository; never modify a development branch.
set -euo pipefail
[[ $# == 1 ]] || { echo "usage: $0 NEW_DIRECTORY" >&2; exit 2; }
[[ ! -e $1 ]] || { echo "destination already exists" >&2; exit 1; }
mkdir -p "$1"
dest=$(realpath "$1")
for project in linux-aurora omarchy-mac-installer; do
    git init --bare "$dest/$project.git"
    git -C "$dest/$project.git" remote add origin "https://github.com/omacom/$project.git"
done
git -C "$dest/linux-aurora.git" fetch --no-tags origin \
    refs/pull/421/head:refs/heads/pr-421 refs/pull/422/head:refs/heads/pr-422
git -C "$dest/omarchy-mac-installer.git" fetch --no-tags origin \
    refs/pull/208/head:refs/heads/pr-208
for hash in 5f3511a0e7e93395a83273946947e84cb93bf593 \
    a17e540a0df57cb4b304b15212a5f3eb5de45037 \
    00e88f127ec23bee3605e54c7bd9338ff022980f; do
    git -C "$dest/linux-aurora.git" merge-base --is-ancestor "$hash" refs/heads/pr-421
done
for project in linux-aurora omarchy-mac-installer; do
    git -C "$dest/$project.git" show-ref > "$dest/$project.refs"
done
echo "Fetched source only. Review dependencies before porting to the M4 kernel."
