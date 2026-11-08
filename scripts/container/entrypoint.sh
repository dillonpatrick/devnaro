#!/usr/bin/env sh
set -eu

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
