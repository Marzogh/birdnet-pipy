# System Administration & Architecture

This document details the internal architecture, service management, and advanced configuration of BirdNET-PiPy.

## Directory Structure

### Runtime Control (`deployment/`)
- **`birdnet-service.sh`**: The master orchestration script. managed by systemd. It handles:
  - Docker container lifecycle
  - Audio backend detection and startup (PulseAudio vs PipeWire)
  - Auto-updates via git

### Audio Configuration (`deployment/audio/`)
- Includes PulseAudio configs (`system.pa`, `daemon.conf`) for running in system-wide mode on RPi OS Lite.
- Icecast streaming server configuration.

---

For audio architecture details, see **[Audio Architecture](../docs/ARCHITECTURE.md#audio-architecture)** in the Architecture docs.

---

## Service Management

The system runs as a standard systemd service named `birdnet-pipy`.

### Basic Controls

```bash
sudo systemctl start birdnet-pipy    # Start
sudo systemctl stop birdnet-pipy     # Stop
sudo systemctl restart birdnet-pipy  # Restart
sudo systemctl status birdnet-pipy   # Check Status
```

### Viewing Logs

**Service Controller Logs** (Wrapper script output):
```bash
journalctl -u birdnet-pipy -f
```

**Application Logs** (Inner container output):
```bash
cd ~/BirdNET-PiPy
docker compose logs -f [container_name]
# containers: main, api, model-server, frontend, icecast
```

---

## Maintenance Triggers

You can trigger maintenance tasks by touching flag files, avoiding full reboots.

| Trigger File | Action | Description |
|--------------|--------|-------------|
| `data/flags/restart-backend` | **Restart** | Restarts all Docker containers. Useful after config changes. |
| `data/flags/update-requested` | **Update** | Runs `install.sh --update` which syncs code, rebuilds images, and updates system configs. |

**Example:**
```bash
# Trigger an update (content is the target branch)
echo "main" > ~/BirdNET-PiPy/data/flags/update-requested
```

### Update Channels

BirdNET-PiPy supports two update channels, configurable in Settings:

| Channel | Branch | Description |
|---------|--------|-------------|
| **Release** | `main` | Stable releases (default) |
| **Latest** | `staging` | Newest features, may be less stable |

When you trigger an update, the system checks for updates from the configured channel's branch.

### Update Flow Details

When an update is triggered, `install.sh --update` performs:
1. Stops Docker containers
2. Fetches and syncs to the target branch (git fetch + checkout + reset)
3. Rebuilds Docker images
4. Updates system configs (PulseAudio, systemd service, sudoers)
5. Exits for systemd to restart the service

**Manual update (current branch):**
```bash
cd ~/BirdNET-PiPy && sudo ./install.sh --update
```

**Manual update (specific branch):**
```bash
cd ~/BirdNET-PiPy && sudo ./install.sh --update --branch staging
```

**Note:** For existing installations before this feature was added, run `sudo ./install.sh` once to update the sudoers configuration for automatic updates.

---

## External Media Storage

BirdNET-PiPy can store recordings, extracted clips, and spectrograms in one
explicitly configured host directory. The database and application settings
remain in `./data`.

1. Mount the drive on the host and create a directory that the BirdNET-PiPy
   service user can write to:

   ```bash
   sudo mkdir -p /mnt/birdnet-media
   sudo chown "$(id -u):$(id -g)" /mnt/birdnet-media
   ```

2. Add the host directory to `~/BirdNET-PiPy/.env`:

   ```bash
   BIRDNET_MEDIA_PATH=/mnt/birdnet-media
   ```

   To choose between several drives in the Settings UI, set this to their
   common parent instead. Only direct child mount points are offered as drives:

   ```bash
   BIRDNET_MEDIA_PATH=/media/birdnet
   ```

3. Restart the service, choose **External media** under **Settings → Storage**,
   then select the drive. Choose **SD card / internal storage** to switch back:

   ```bash
   sudo systemctl restart birdnet-pipy
   ```

Media is written below a `BirdNET-PiPy/` subdirectory on that target. If the
directory is absent or not writable, new media falls back to internal storage;
existing internal files remain readable. Use a stable mount configured in
`/etc/fstab` so a removable drive does not acquire a different path after boot.

For host safety, only `BIRDNET_MEDIA_PATH` is exposed to the containers; the
application does not mount or scan the host's full `/media` or `/mnt` trees.

---

## Troubleshooting

### No Audio Being Recorded

```bash
# Verify PulseAudio is running on host
pactl info

# List available audio sources
pactl list sources short
```

### Live Stream Not Working

```bash
# Check if Icecast is receiving audio
curl -s http://localhost:8888/status-json.xsl | grep -o '"listeners":[0-9]*'

# Test stream directly
curl http://localhost:8888/stream.mp3 --max-time 3 -o /dev/null && echo "Stream OK"
```

**Icecast Web Interface:** http://localhost:8888/status.xsl

---

## Icecast Configuration

### Change Stream Bitrate

Set environment variable before starting containers:
```bash
export STREAM_BITRATE=192k  # Default is 128k
docker compose up -d
```

### Change Icecast Passwords

By default, a **random 16-character password** is generated each time the Icecast container starts. This is secure but means the password changes on restart.

To set a **persistent password**, set the environment variable:
```bash
export ICECAST_PASSWORD=your_secure_password
docker compose up -d
```

**Note:** There is no static Icecast config: the startup script generates a secure one at runtime.
