#!/usr/bin/env python3
"""AOC 8R1 fixed-firmware backup/boot writer; RAM USBPlug must be running.

Public adaptation: offline tests only; not reflashed on hardware after cleanup.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parent.parent
BOOT_LBA = 55296
BOOT_SECTORS = 131072
BOOT_BYTES = 67108864
RECOVERY_LBA = 194560
RECOVERY_SECTORS = 196608
CAPACITY = 123011072
UBOOT_HASH = '3f38b7bd3f2cd8607db05bec8fd98cbd1a5f8fab0fd04e0a213293eb35b1f670'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def validate_gpt(data, expected):
    require(len(data) == 64 * 512, 'Incomplete GPT read')
    header = bytearray(data[512:1024])
    require(header[:8] == b'EFI PART', 'GPT signature missing; check RAM reader')
    size, stored_crc = struct.unpack_from('<II', header, 12)
    require(92 <= size <= 512, 'Invalid GPT header size')
    struct.pack_into('<I', header, 16, 0)
    require(zlib.crc32(header[:size]) == stored_crc, 'GPT header CRC mismatch')
    current_lba, backup_lba = struct.unpack_from('<QQ', header, 24)
    require(current_lba == 1 and backup_lba == CAPACITY - 1, 'GPT capacity mismatch')
    entry_lba, count, stride, entries_crc = struct.unpack_from('<QIII', header, 72)
    require(128 <= stride <= 512 and 0 < count <= 128, 'Unexpected GPT table format')
    start = entry_lba * 512
    entries = data[start:start + count * stride]
    require(len(entries) == count * stride, 'GPT entries exceed primary read')
    require(zlib.crc32(entries) == entries_crc, 'GPT entries CRC mismatch')
    partitions = {}
    for offset in range(0, len(entries), stride):
        entry = entries[offset:offset + stride]
        if entry[:16] == bytes(16):
            continue
        first, last = struct.unpack_from('<QQ', entry, 32)
        name = entry[56:128].decode('utf-16le').split('\0', 1)[0]
        require(name not in partitions and last >= first, 'Invalid or duplicate GPT entry')
        partitions[name] = (first, last - first + 1)
    wanted = {p['name']: (p['start_sector'], p['sector_count']) for p in expected}
    require(partitions == wanted, 'Partition layout differs from validated sample')


class Session:
    def __init__(self, root, tool):
        self.root = Path(root)
        self.work = self.root / 'work'
        self.work.mkdir(exist_ok=True)
        self.tool = str(Path(tool).resolve())
        self.manifest = json.loads((self.root / 'manifests/files.json').read_text())
        self.partitions = json.loads((self.root / 'manifests/partitions.json').read_text())['partitions']

    def asset(self, name):
        path = self.root / 'assets' / name
        spec = self.manifest['files'][name]
        require(path.is_file(), f'Missing assets/{name}; see docs/ROOT_GUIDE.md')
        require(path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'], f'Invalid asset {name}')
        return path

    def check_files(self):
        for name, spec in self.manifest['files'].items():
            if spec.get('required_for_boot'):
                self.asset(name)
        print('Required local image / RAM utility hashes: PASS')

    def run(self, args, label, timeout=120):
        result = subprocess.run([self.tool] + args, cwd=self.work, capture_output=True, timeout=timeout)
        (self.work / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, f'{label} failed; inspect work/{label}.log')
        return result.stdout.decode(errors='replace')

    def read(self, lba, sectors, name):
        path = self.work / name
        self.run(['rl', str(lba), str(sectors), str(path)], 'read-' + name)
        require(path.stat().st_size == sectors * 512, f'Incomplete read: {name}')
        return path

    def validate_device(self):
        devices = self.run(['ld'], 'device-list', 10)
        require(devices.count('DevNo=') == 1 and 'Vid=0x2207,Pid=0x350a' in devices,
                'Require exactly one matching Rockusb target; disconnect others')
        require('123011072 Sectors' in self.run(['rfi'], 'flash-info', 10), 'Capacity differs')
        gpt = self.read(0, 64, 'gpt-readback.bin')
        validate_gpt(gpt.read_bytes(), self.partitions)
        uboot = self.read(16384, 8192, 'uboot-readback.img')
        require(digest(uboot) == UBOOT_HASH, 'U-Boot differs from sample')
        # Working RAM USBPlug may still enumerate as Maskrom. Verify an actual
        # read above 32 MiB rather than trusting the enumeration mode label.
        probe = self.read(RECOVERY_LBA, 1, 'recovery-high-read-probe.bin')
        with self.asset('recovery-original-verified.img').open('rb') as stream:
            expected = stream.read(512)
        require(probe.read_bytes() == expected, 'High-LBA read invalid; load validated RAM USBPlug')

    def verify_image(self, path, asset_name):
        spec = self.manifest['files'][asset_name]
        require(path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'],
                f'{path.name} differs; do not write this firmware')

    def backup(self):
        for name in ('boot-original-local.img', 'recovery-original-local.img', 'backup-receipt.json'):
            require(not (self.work / name).exists(), f'Existing {name}; preserve it, do not overwrite')
        boot = self.read(BOOT_LBA, BOOT_SECTORS, 'boot-original-local.img')
        self.verify_image(boot, 'boot-original-verified.img')
        recovery = self.read(RECOVERY_LBA, RECOVERY_SECTORS, 'recovery-original-local.img')
        self.verify_image(recovery, 'recovery-original-verified.img')
        receipt = {'boot_sha256': digest(boot), 'recovery_sha256': digest(recovery),
                   'capacity_sectors': CAPACITY, 'uboot_sha256': UBOOT_HASH}
        (self.work / 'backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('Own boot / Recovery backups verified. Copy work backups to reliable storage.')

    def local_original(self):
        receipt = json.loads((self.work / 'backup-receipt.json').read_text())
        spec = self.manifest['files']['boot-original-verified.img']
        require(receipt.get('boot_sha256') == spec['sha256'] and receipt.get('uboot_sha256') == UBOOT_HASH
                and receipt.get('capacity_sectors') == CAPACITY, 'Invalid local backup receipt')
        path = self.work / 'boot-original-local.img'
        self.verify_image(path, 'boot-original-verified.img')
        return path

    def write_verified(self, path, asset_name, label):
        self.run(['wl', str(BOOT_LBA), str(path)], label)
        readback = self.read(BOOT_LBA, BOOT_SECTORS, label + '-readback.img')
        self.verify_image(readback, asset_name)

    def write(self, action, allow_write=False):
        require(allow_write, 'Write requires explicit --allow-write; no write performed')
        original = self.local_original()
        if action == 'restore-original':
            self.write_verified(original, 'boot-original-verified.img', 'restore-original')
            print('Original boot restored; full partition hash verified. Reboot separately.')
            return
        candidate = self.asset('boot-magisk-v31.1.img')
        before = self.read(BOOT_LBA, BOOT_SECTORS, 'before-write-boot.img')
        self.verify_image(before, 'boot-original-verified.img')
        try:
            self.write_verified(candidate, 'boot-magisk-v31.1.img', 'write-candidate')
        except BaseException as write_error:
            try:
                self.write_verified(original, 'boot-original-verified.img', 'rollback-original')
            except BaseException as rollback_error:
                raise RuntimeError('Write failed AND rollback failed; keep backups, follow docs/ROLLBACK.md') from rollback_error
            raise RuntimeError('Write failed; original boot restored and verified') from write_error
        print('Magisk boot written; full readback verified. Reboot and verify root separately.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check-files', 'backup', 'write-candidate', 'restore-original'])
    parser.add_argument('--tool', type=Path, default=ROOT / 'assets/rkdeveloptool-macos-arm64')
    parser.add_argument('--allow-write', action='store_true')
    args = parser.parse_args()
    session = Session(ROOT, args.tool)
    session.check_files()
    if args.action == 'check-files':
        return
    if args.action in ('write-candidate', 'restore-original'):
        require(args.allow_write, 'Write requires --allow-write; no device command issued')
    session.validate_device()
    if args.action == 'backup':
        session.backup()
    else:
        session.write(args.action, args.allow_write)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'STOP: {error}', file=sys.stderr)
        sys.exit(1)
