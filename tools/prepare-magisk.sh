#!/system/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Run on Android from a disposable directory containing the official patcher,
# ARM64 payloads (magiskboot, magiskinit, magisk, init-ld), and original boot.img.
# Produces new-boot.img only. Does not install or flash.
# Official boot_patch.sh deliberately checks non-zero probe exit statuses and
# references unset variables. Do not enable shell errexit/nounset around it.
for file in boot.img boot_patch.sh magiskboot magiskinit magisk init-ld; do
    [ -f "$file" ] || { echo "Missing $file" >&2; exit 1; }
done
[ ! -e new-boot.img ] || { echo 'new-boot.img already exists' >&2; exit 1; }
export SOURCEDMODE=true BOOTMODE=false
export KEEPVERITY=true KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false
export RECOVERYMODE=false LEGACYSAR=false PREINITDEVICE=metadata
ui_print() { echo "$@"; }
abort() { echo "$@" >&2; exit 1; }
. ./boot_patch.sh ./boot.img
