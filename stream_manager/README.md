# Stream Manager

Smart ONVIF proxy for Home Assistant. Publish a camera, an RTSP URL, an existing ONVIF stream, or a still image as one stable ONVIF device. Optional rules switch the picture from an entity state without changing the RTSP or ONVIF address.

The panel is this add-on. go2rtc 1.9.14 is only the local RTSP engine.

Stream Manager is an independent project. It is not affiliated with or endorsed by Home Assistant, the Open Home Foundation, or ONVIF.

## Options

| Option | Default | Purpose |
| --- | --- | --- |
| `ui_port` | `8099` | Panel port. Ingress expects 8099. |
| `onvif_port` | `8080` | ONVIF device and media HTTP port on the host. |
| `rtsp_port` | `8554` | Stable RTSP port. The path is the camera id. |
| `go2rtc_api_port` | `19841` | Localhost control port for the engine. |
| `poll_seconds` | `5` | How often entity states are polled. |
| `log_level` | `info` | Log verbosity: `debug`, `info`, `warning`, or `error`. Set to `debug` when collecting diagnostics. |

Cameras, rules, and ONVIF passwords are stored in `cameras.json` under the configured data directory (the add-on uses `/data`).

Leave the camera username and password empty for an open device. When they are set, stream and profile calls require a UsernameToken or HTTP Digest. Time and capabilities stay open.

## Addresses

Each camera chooses a host interface. Discovery and the addresses shown to clients use that IP. A source the host can reach on one network can be announced on another.

- ONVIF: `http://<listen-ip>:8080/onvif/<id>/device_service`
- RTSP: `rtsp://<listen-ip>:8554/<id>`

The published stream is one ONVIF Profile S profile, token `main`. Resolution, frame rate, bitrate, H.264 profile, and GOP are encoded into that stream and reported over ONVIF.

RTSP sources are pulled using UDP transport. Ensure UDP media traffic is permitted between the host and each source camera.

For troubleshooting, set the add-on's `log_level` option to `debug`, save, and restart the add-on. Reproduce the issue and share the relevant log lines, including the go2rtc and stream-test entries. Logs redact URL credentials; still review logs before sharing them.

## Install in a Proxmox LXC

The installer runs **inside an existing Debian 12 or newer LXC container** as root. It installs the application and its Python dependencies, ffmpeg, go2rtc, and a systemd service. It does not create or modify the container on the Proxmox host.

For example, from the Proxmox host, enter your running container (replace `106` with its CT ID):

```sh
pct enter 106
```

Then run inside the container:

```sh
curl -fsSL https://raw.githubusercontent.com/VolodymyrLykhachov/Stream-Manager/main/stream_manager/install-lxc.sh | sh
```

The service starts automatically and stores cameras, rules, and other state in `/var/lib/stream-manager`. The installer creates `/etc/default/stream-manager` for ports and optional Home Assistant settings. Edit that file to set `HASP_HA_URL` and `HASP_HA_TOKEN`, then restart the service:

```sh
nano /etc/default/stream-manager
systemctl restart stream-manager
```

Open `http://<LXC-IP>:8099/`. Allow TCP ports `8099` (panel), `8080` (ONVIF), and `8554` (RTSP) through any Proxmox firewall. The go2rtc control port `19841` is bound to localhost only.

WS-Discovery uses UDP multicast port `3702`; the LXC bridge and any firewalls between clients and the container must pass multicast. This does not work across routed networks without a multicast relay.

The service requests `CAP_NET_ADMIN` and `CAP_NET_RAW` for virtual camera addresses, macvlan interfaces, and ARP announcements. The container's Proxmox configuration must permit these capabilities and networking operations for those features. If it does not, the UI and streams can still run, but virtual camera address assignment and discovery announcements may be limited. Keep the LXC attached to the LAN bridge from which clients should discover the cameras.

Check service health and logs with:

```sh
systemctl status stream-manager
journalctl -u stream-manager -f
```

To update, rerun the installer. It fast-forwards the checkout and restarts the service without replacing `/var/lib/stream-manager` or an existing `/etc/default/stream-manager`.

## Run locally

From the repository root, with Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r stream_manager\requirements.txt
cd stream_manager
..\.venv\Scripts\python -m onvif_proxy
```

Open `http://127.0.0.1:8099/`.

Copy `config.example.json` to `config.local.json` and set `ha_url` plus a long-lived access token when you want Home Assistant camera entities and rules. RTSP and image sources work without that file.

Optional engine binary, so picture switching is published on RTSP. Place it on `PATH`, or download the Windows build into the repository `bin` folder:

```powershell
New-Item -ItemType Directory -Force ..\bin | Out-Null
Invoke-WebRequest -Uri "https://github.com/AlexxIT/go2rtc/releases/download/v1.9.14/go2rtc_win64.zip" -OutFile ..\bin\go2rtc.zip
Expand-Archive -Force ..\bin\go2rtc.zip ..\bin
```

Still images need `ffmpeg` on `PATH`. The add-on image installs it.

`HASP_DEV=1` is the default outside Supervisor. `POST /api/dev/states` with `{"switch.example":"on"}` injects states for rule tests. That route is off when `SUPERVISOR_TOKEN` is set.
