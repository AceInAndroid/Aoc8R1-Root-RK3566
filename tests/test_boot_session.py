"""Offline failure-path tests; no adb, Rockusb, or connected device is used."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import boot_session as boot


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SimulatedSession(boot.Session):
    """Tiny payloads model reads/writes and corrupt USB readback, without USB."""
    def __init__(self, root):
        self.root = Path(root)
        self.work = self.root / 'work'
        self.work.mkdir()
        (self.root / 'assets').mkdir()
        self.original = b'original boot'
        self.candidate = b'magisk boot'
        self.device = self.original
        self.corrupt_candidate = False
        self.fail_rollback = False
        self.calls = []
        self.manifest = {'files': {}}
        for name, data in [('boot-original-verified.img', self.original),
                           ('boot-magisk-v31.1.img', self.candidate)]:
            (self.root / 'assets' / name).write_bytes(data)
            self.manifest['files'][name] = {'bytes': len(data), 'sha256': sha(data)}
        (self.work / 'boot-original-local.img').write_bytes(self.original)
        (self.work / 'backup-receipt.json').write_text(json.dumps({
            'boot_sha256': sha(self.original), 'uboot_sha256': boot.UBOOT_HASH,
            'capacity_sectors': boot.CAPACITY,
        }))

    def run(self, args, label, timeout=120):
        self.calls.append(args)
        if args[0] != 'wl':
            raise AssertionError('Unexpected simulated command')
        if self.fail_rollback and label == 'rollback-original':
            raise RuntimeError('Simulated disconnected USB during rollback')
        self.device = Path(args[2]).read_bytes()
        if self.corrupt_candidate and label == 'write-candidate':
            self.device = b'corrupt readback'

    def read(self, lba, sectors, name):
        self.calls.append(['rl', lba, sectors])
        if (lba, sectors) != (boot.BOOT_LBA, boot.BOOT_SECTORS):
            raise AssertionError('Unexpected partition')
        path = self.work / name
        path.write_bytes(self.device)
        return path


class WriteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.s = SimulatedSession(self.temp.name)

    def writes(self):
        return [a for a in self.s.calls if a[0] == 'wl']

    def test_no_write_without_flag(self):
        with self.assertRaisesRegex(RuntimeError, '--allow-write'):
            self.s.write('write-candidate')
        self.assertEqual(self.s.calls, [])

    def test_missing_receipt_stops(self):
        (self.s.work / 'backup-receipt.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.s.write('write-candidate', True)
        self.assertEqual(self.writes(), [])

    def test_wrong_current_boot_stops_before_write(self):
        self.s.device = b'other firmware'
        with self.assertRaisesRegex(RuntimeError, 'differs'):
            self.s.write('write-candidate', True)
        self.assertEqual(self.writes(), [])

    def test_corrupt_asset_stops_before_write(self):
        (self.s.root / 'assets/boot-magisk-v31.1.img').write_bytes(b'bad')
        with self.assertRaisesRegex(RuntimeError, 'Invalid asset'):
            self.s.write('write-candidate', True)
        self.assertEqual(self.writes(), [])

    def test_success_writes_only_fixed_boot_and_reads_back(self):
        self.s.write('write-candidate', True)
        self.assertEqual(len(self.writes()), 1)
        self.assertEqual(self.writes()[0][1], str(boot.BOOT_LBA))
        self.assertEqual(self.s.device, self.s.candidate)
        self.assertEqual(len([a for a in self.s.calls if a[0] == 'rl']), 2)

    def test_corrupt_readback_restores_original(self):
        self.s.corrupt_candidate = True
        with self.assertRaisesRegex(RuntimeError, 'original boot restored and verified'):
            self.s.write('write-candidate', True)
        self.assertEqual(len(self.writes()), 2)
        self.assertEqual(self.s.device, self.s.original)

    def test_failed_rollback_is_reported(self):
        self.s.corrupt_candidate = True
        self.s.fail_rollback = True
        with self.assertRaisesRegex(RuntimeError, 'rollback failed'):
            self.s.write('write-candidate', True)

    def test_restore_verifies_original(self):
        self.s.device = b'failed boot'
        self.s.write('restore-original', True)
        self.assertEqual(self.s.device, self.s.original)
        self.assertEqual(len(self.writes()), 1)
        self.assertTrue((self.s.work / 'restore-original-readback.img').exists())


def gpt_fixture(parts):
    data = bytearray(64 * 512)
    entries = bytearray(128 * 128)
    for index, part in enumerate(parts):
        offset = index * 128
        entries[offset:offset + 16] = b'\x01' * 16
        struct.pack_into('<QQ', entries, offset + 32, part['start_sector'],
                         part['start_sector'] + part['sector_count'] - 1)
        name = part['name'].encode('utf-16le')
        entries[offset + 56:offset + 56 + len(name)] = name
    header = bytearray(512)
    header[:8] = b'EFI PART'
    struct.pack_into('<III', header, 8, 0x10000, 92, 0)
    struct.pack_into('<QQ', header, 24, 1, boot.CAPACITY - 1)
    struct.pack_into('<QIII', header, 72, 2, 128, 128, zlib.crc32(entries))
    struct.pack_into('<I', header, 16, zlib.crc32(header[:92]))
    data[512:1024] = header
    data[1024:1024 + len(entries)] = entries
    return bytes(data)


class DeviceTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.parts = json.loads((root / 'manifests/partitions.json').read_text())['partitions']

    def test_valid_gpt(self):
        boot.validate_gpt(gpt_fixture(self.parts), self.parts)

    def test_cc_filler_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'GPT signature'):
            boot.validate_gpt(b'\xcc' * (64 * 512), self.parts)

    def test_gpt_corrupt_crc(self):
        data = bytearray(gpt_fixture(self.parts))
        data[1024] ^= 1
        with self.assertRaisesRegex(RuntimeError, 'entries CRC'):
            boot.validate_gpt(data, self.parts)

    def test_other_layout_rejected_even_with_valid_crcs(self):
        parts = [dict(p) for p in self.parts]
        parts[0]['start_sector'] += 1
        with self.assertRaisesRegex(RuntimeError, 'layout differs'):
            boot.validate_gpt(gpt_fixture(parts), self.parts)

    def test_multiple_devices_rejected_before_reads(self):
        session = boot.Session.__new__(boot.Session)
        session.run = Mock(return_value='DevNo=1 Vid=0x2207,Pid=0x350a\nDevNo=2 Vid=0x2207,Pid=0x350a')
        session.read = Mock()
        with self.assertRaisesRegex(RuntimeError, 'exactly one'):
            session.validate_device()
        session.read.assert_not_called()

    def test_ram_usbplug_can_enumerate_maskrom_and_still_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpt = root / 'gpt.bin'
            gpt.write_bytes(gpt_fixture(self.parts))
            uboot = root / 'uboot.img'
            uboot.write_bytes(b'uboot fixture')
            recovery = root / 'recovery.img'
            recovery.write_bytes(b'ANDROID!' + bytes(504))
            probe = root / 'probe.bin'
            probe.write_bytes(recovery.read_bytes())
            session = boot.Session.__new__(boot.Session)
            session.partitions = self.parts
            session.run = Mock(side_effect=[
                'DevNo=1\tVid=0x2207,Pid=0x350a,LocationID=3\tMaskrom',
                'Flash Size: 123011072 Sectors',
            ])
            session.read = Mock(side_effect=[gpt, uboot, probe])
            session.asset = Mock(return_value=recovery)
            from unittest.mock import patch
            with patch.object(boot, 'digest', return_value=boot.UBOOT_HASH):
                session.validate_device()
            self.assertEqual(session.read.call_args_list[-1].args[:2], (boot.RECOVERY_LBA, 1))

    def test_high_lba_cc_filler_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpt = root / 'gpt.bin'
            gpt.write_bytes(gpt_fixture(self.parts))
            original = root / 'recovery.img'
            original.write_bytes(b'ANDROID!' + bytes(504))
            probe = root / 'probe.bin'
            probe.write_bytes(b'\xcc' * 512)
            session = boot.Session.__new__(boot.Session)
            session.partitions = self.parts
            session.run = Mock(side_effect=[
                'DevNo=1 Vid=0x2207,Pid=0x350a Loader',
                '123011072 Sectors',
            ])
            session.read = Mock(side_effect=[gpt, original, probe])
            session.asset = Mock(return_value=original)
            from unittest.mock import patch
            with patch.object(boot, 'digest', return_value=boot.UBOOT_HASH):
                with self.assertRaisesRegex(RuntimeError, 'High-LBA read invalid'):
                    session.validate_device()


if __name__ == '__main__':
    unittest.main()
