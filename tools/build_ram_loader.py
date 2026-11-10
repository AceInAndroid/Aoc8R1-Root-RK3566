#!/usr/bin/env python3
"""Reproduce the validated RAM-only container offline, without USB access.

SPDX-License-Identifier: GPL-3.0-or-later
Container structure follows Rockchip rkdeveloptool boot_merger.h / RKBoot.cpp.
Only the pinned USBPlug and original sample DDR are accepted.
"""
import argparse
import hashlib
from pathlib import Path
import struct

DDR_HASH = '93b27b55bab72521bef3753e50d647cddccfc1822fe954f3324e4ca6860a5ba7'
USB_HASH = '4038b7857b840f539760decc0daf1601b8ff61cc17798101e93b11128a7f333e'
OUTPUT_HASH = 'bef69d6d3c513af830182d9689673e5953df6749417508d87f150f90d6fb806d'


def checked_read(path, size, expected):
    data = Path(path).read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Wrong input: {Path(path).name}')
    return data


def rockchip_crc(data):
    # MSB first, polynomial 0x04c10db7, initial 0, no final xor.
    table = []
    for value in range(256):
        crc = value << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04c10db7 if crc & 0x80000000 else 0)) & 0xffffffff
        table.append(crc)
    crc = 0
    for value in data:
        crc = ((crc << 8) ^ table[(crc >> 24) ^ value]) & 0xffffffff
    return crc


def build(ddr, usb):
    usb = bytearray(usb)
    if usb[0x975c:0x9760] != bytes.fromhex('2800a052'):
        raise ValueError('Unexpected USBPlug instruction')
    usb[0x975c:0x9760] = bytes.fromhex('08008012')
    # Boot download entries are padded to 2048-byte boundaries.
    usb += bytes((-len(usb)) % 2048)
    output = bytearray(0xf000 + len(usb))
    struct.pack_into('<I H I I', output, 0, 0x544f4f42, 102, 0x100, 0x01030000)
    struct.pack_into('<H5B', output, 14, 2026, 11, 10, 0, 0, 0)
    struct.pack_into('<I', output, 21, 0x33353638)
    struct.pack_into('<BIBBIBBIBBB', output, 25, 1, 102, 57, 1, 159, 57, 0, 216, 57, 0, 1)
    for index, kind, name, offset, payload, delay in [
        (0, 1, 'DDR-original', 0x800, ddr, 10),
        (1, 2, 'USBPlug-official', 0xf000, usb, 100),
    ]:
        entry = struct.pack('<BI40sIII', 57, kind, name.encode('utf-16le'), offset, len(payload), delay)
        output[102 + 57 * index:159 + 57 * index] = entry
        output[offset:offset + len(payload)] = payload
    output += struct.pack('<I', rockchip_crc(output))
    if hashlib.sha256(output).hexdigest() != OUTPUT_HASH:
        raise ValueError('Container does not match validated sample')
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ddr', type=Path, default=Path('assets/ddr-original.bin'))
    parser.add_argument('--usbplug', type=Path, default=Path('assets/rk356x_usbplug_v1.17.bin'))
    parser.add_argument('--output', type=Path, default=Path('work/ram-loader-reproduced.bin'))
    args = parser.parse_args()
    data = build(checked_read(args.ddr, 59392, DDR_HASH), checked_read(args.usbplug, 98708, USB_HASH))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(data)
    print(f'{OUTPUT_HASH}  {args.output} ({len(data)} bytes; RAM download only)')


if __name__ == '__main__':
    main()
