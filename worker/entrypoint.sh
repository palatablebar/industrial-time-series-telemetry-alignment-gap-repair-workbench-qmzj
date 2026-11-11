#!/usr/bin/env bash
# Celery worker + heartbeat file consumed by worker/healthy.py
set -euo pipefail
HEARTBEAT=/tmp/tsalign-worker-heartbeat
touch "$HEARTBEAT"

( while true; do touch "$HEARTBEAT"; sleep 5; done ) &
HEARTBEAT_PID=$!
trap 'kill "$HEARTBEAT_PID" 2>/dev/null || true' EXIT

exec celery -A src.config.celery_app worker --loglevel=INFO --concurrency=2
