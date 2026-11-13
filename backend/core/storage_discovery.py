"""Read the host service's device inventory, without accessing block devices."""
import json
import os
import time

from config.settings import BASE_DIR

SNAPSHOT_PATH = os.path.join(BASE_DIR, 'data/flags/storage-devices.json')
MAX_AGE_SECONDS = 60
_SYSTEM_MOUNTS = {'/', '/boot', '/boot/firmware'}


def _nodes(device):
    yield device
    for child in device.get('children', []):
        yield from _nodes(child)


def describe_devices(blockdevices):
    """Select USB disks and NVMe/SATA/SAS SSDs, retaining mount metadata."""
    drives = []
    for disk in blockdevices:
        if disk.get('type') != 'disk':
            continue
        bus = (disk.get('tran') or '').lower()
        ssd = bus == 'nvme' or (bus in ('sata', 'sas') and disk.get('rota') in (False, 0, '0'))
        if bus != 'usb' and not ssd:
            continue
        nodes = list(_nodes(disk))
        mounts = sorted({mount for node in nodes for mount in (node.get('mountpoints') or []) if mount})
        filesystems = sorted({node['fstype'] for node in nodes if node.get('fstype')})
        path = disk.get('path') or '/dev/' + disk['name']
        drives.append({
            'path': path,
            'name': (disk.get('model') or disk.get('label') or disk['name']).strip(),
            'size_bytes': int(disk.get('size') or 0),
            'connection': bus.upper(),
            'filesystems': filesystems,
            'mount_points': mounts,
            'mounted': bool(mounts),
            'system_drive': bool(_SYSTEM_MOUNTS.intersection(mounts)),
            'read_only': disk.get('ro') in (True, 1, '1'),
        })
    return sorted(drives, key=lambda drive: drive['path'])


def get_storage_devices():
    try:
        with open(SNAPSHOT_PATH) as stream:
            updated_at = os.fstat(stream.fileno()).st_mtime
            payload = json.load(stream)
        if time.time() - updated_at > MAX_AGE_SECONDS:
            return {'state': 'unavailable', 'devices': [],
                    'message': 'Drive discovery is not updating.'}
        return {'state': 'available', 'updated_at': updated_at,
                'devices': describe_devices(payload['blockdevices'])}
    except FileNotFoundError:
        return {'state': 'unavailable', 'devices': [],
                'message': 'Drive discovery is not available on this installation.'}
    except (OSError, ValueError, KeyError, TypeError):
        return {'state': 'unavailable', 'devices': [],
                'message': 'Drive information could not be read.'}
