"""Read-only host inventory parsing and freshness checks."""
import json
import os
import time


def test_usb_ssds_and_system_drive_are_identified_without_actions():
    from core.storage_discovery import describe_devices
    devices = describe_devices([
        {'name': 'sda', 'path': '/dev/sda', 'type': 'disk', 'tran': 'usb',
         'model': 'USB SSD', 'size': 500000000000, 'rota': False, 'ro': False,
         'children': [{'name': 'sda1', 'fstype': 'exfat', 'mountpoints': [None]}]},
        {'name': 'nvme0n1', 'type': 'disk', 'tran': 'nvme', 'model': 'Boot SSD',
         'size': 256000000000, 'children': [
             {'name': 'nvme0n1p2', 'fstype': 'ext4', 'mountpoints': ['/']}]},
        {'name': 'sdb', 'type': 'disk', 'tran': 'sata', 'rota': True},
        {'name': 'loop0', 'type': 'loop', 'rota': False},
    ])
    assert len(devices) == 2
    usb = next(d for d in devices if d['connection'] == 'USB')
    assert usb['name'] == 'USB SSD'
    assert usb['size_bytes'] == 500000000000
    assert usb['filesystems'] == ['exfat']
    assert not usb['mounted']
    system = next(d for d in devices if d['system_drive'])
    assert system['mounted'] and system['mount_points'] == ['/']


def test_snapshot_is_read_only_and_stale_inventory_is_not_presented_as_current(tmp_path, monkeypatch):
    import core.storage_discovery as discovery
    snapshot = tmp_path / 'storage-devices.json'
    raw = json.dumps({'blockdevices': [{'name': 'sda', 'type': 'disk', 'tran': 'usb',
                                      'model': 'USB', 'size': 1000}]})
    snapshot.write_text(raw)
    monkeypatch.setattr(discovery, 'SNAPSHOT_PATH', str(snapshot))
    assert discovery.get_storage_devices()['state'] == 'available'
    assert snapshot.read_text() == raw
    old = time.time() - discovery.MAX_AGE_SECONDS - 1
    os.utime(snapshot, (old, old))
    assert discovery.get_storage_devices()['state'] == 'unavailable'
