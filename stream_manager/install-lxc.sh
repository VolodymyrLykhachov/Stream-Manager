#!/bin/sh
set -eu

REPOSITORY=${STREAM_MANAGER_REPOSITORY:-https://github.com/VolodymyrLykhachov/Stream-Manager.git}
BRANCH=${STREAM_MANAGER_BRANCH:-main}
INSTALL_ROOT=/opt/stream-manager
SOURCE_DIR=$INSTALL_ROOT/src
VENV_DIR=$INSTALL_ROOT/venv
DATA_DIR=/var/lib/stream-manager
GO2RTC_VERSION=1.9.14

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

[ "$(id -u)" -eq 0 ] || fail "run this installer as root inside the Debian LXC."
[ -r /etc/os-release ] || fail "this installer supports Debian-based LXC containers only."
. /etc/os-release
case "${ID:-}" in
  debian) ;;
  *) fail "unsupported operating system: ${PRETTY_NAME:-unknown}; use Debian 12 or newer." ;;
esac
case "${VERSION_ID%%.*}" in
  12|13|14|15) ;;
  *) fail "unsupported Debian release: ${VERSION_ID:-unknown}; use Debian 12 or newer." ;;
esac

command -v apt-get >/dev/null 2>&1 || fail "apt-get is required."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl ffmpeg git iproute2 nftables python3 python3-venv

if [ -d "$SOURCE_DIR/.git" ]; then
  if [ -n "$(git -C "$SOURCE_DIR" status --porcelain)" ]; then
    fail "$SOURCE_DIR has local changes; save them before updating."
  fi
  git -C "$SOURCE_DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$SOURCE_DIR" switch --detach FETCH_HEAD
elif [ -e "$SOURCE_DIR" ]; then
  fail "$SOURCE_DIR exists and is not a Git checkout; move it before installing."
else
  install -d "$INSTALL_ROOT"
  git clone --depth 1 --branch "$BRANCH" "$REPOSITORY" "$SOURCE_DIR"
fi

APP_DIR=$SOURCE_DIR/stream_manager
[ -f "$APP_DIR/onvif_proxy/__main__.py" ] || fail "the repository does not contain the Stream Manager application."

case "$(dpkg --print-architecture)" in
  amd64) GO2RTC_ASSET=go2rtc_linux_amd64 ;;
  arm64) GO2RTC_ASSET=go2rtc_linux_arm64 ;;
  armhf) GO2RTC_ASSET=go2rtc_linux_armv6 ;;
  i386) GO2RTC_ASSET=go2rtc_linux_i386 ;;
  *) fail "unsupported Debian architecture: $(dpkg --print-architecture)." ;;
esac

install -d "$INSTALL_ROOT" "$DATA_DIR"
if ! getent group stream-manager >/dev/null 2>&1; then
  groupadd --system stream-manager
fi
if ! getent passwd stream-manager >/dev/null 2>&1; then
  useradd --system --gid stream-manager --home-dir "$DATA_DIR" --shell /usr/sbin/nologin stream-manager
fi
chown -R stream-manager:stream-manager "$DATA_DIR"
chmod 0750 "$DATA_DIR"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check --upgrade -r "$APP_DIR/requirements.txt"

tmp_binary=$(mktemp)
trap 'rm -f "$tmp_binary"' EXIT HUP INT TERM
curl --fail --location --silent --show-error \
  "https://github.com/AlexxIT/go2rtc/releases/download/v${GO2RTC_VERSION}/${GO2RTC_ASSET}" \
  --output "$tmp_binary"
install -m 0755 "$tmp_binary" /usr/local/bin/go2rtc
rm -f "$tmp_binary"
trap - EXIT HUP INT TERM

install -m 0644 "$APP_DIR/stream-manager.service" /etc/systemd/system/stream-manager.service
if [ ! -e /etc/default/stream-manager ]; then
  install -m 0600 "$APP_DIR/stream-manager.env.example" /etc/default/stream-manager
fi
chown root:root /etc/default/stream-manager
chmod 0600 /etc/default/stream-manager

systemctl daemon-reload
systemctl enable stream-manager.service
systemctl restart stream-manager.service
systemctl is-active --quiet stream-manager.service || {
  systemctl --no-pager --full status stream-manager.service >&2 || true
  fail "Stream Manager did not start; inspect the service logs."
}

printf '\nStream Manager is installed and enabled.\n'
printf 'Panel:  http://<LXC-IP>:8099/\n'
printf 'ONVIF:  http://<LXC-IP>:8080/onvif/<camera-id>/device_service\n'
printf 'RTSP:   rtsp://<LXC-IP>:8554/<camera-id>\n'
printf 'Config: /etc/default/stream-manager and %s/options.json\n' "$DATA_DIR"
printf 'Status: systemctl status stream-manager\n'
