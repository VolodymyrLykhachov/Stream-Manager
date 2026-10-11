#!/bin/sh
cd /app || exit 1
exec python3 -m onvif_proxy
