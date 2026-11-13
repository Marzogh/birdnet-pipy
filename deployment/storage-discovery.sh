#!/bin/bash
# Read host device metadata only. No mounting or disk writes.
set -eu

if [ "$#" -ne 1 ]; then
    echo 'Usage: storage-discovery.sh OUTPUT_JSON' >&2
    exit 2
fi
if ! command -v lsblk >/dev/null 2>&1; then
    echo 'Drive discovery unavailable: lsblk is not installed.' >&2
    exit 1
fi

snapshot="$1"
if [ -t 1 ]; then
    echo 'Reading connected-drive metadata (read-only)...'
fi
mkdir -p "$(dirname "$snapshot")"
temporary=$(mktemp "${snapshot}.XXXXXX")
trap 'rm -f "$temporary"' EXIT
timeout 10 lsblk --json --bytes --output NAME,PATH,TYPE,SIZE,MODEL,TRAN,ROTA,RO,FSTYPE,LABEL,MOUNTPOINTS > "$temporary"
chmod 644 "$temporary"
mv -f "$temporary" "$snapshot"
if [ -t 1 ]; then
    echo 'Drive information refreshed.'
fi
