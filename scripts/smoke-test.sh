#!/usr/bin/env bash
set -euo pipefail
image="${1:?image required}"
container="baidu-autosave-smoke"
temp_dir="$(mktemp -d)"
cleanup() {
  docker logs "$container" || true
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -rf "$temp_dir"
}
trap cleanup EXIT
docker pull "$image"
docker run -d --name "$container" -p 127.0.0.1:5000:5000 \
  -e ADMIN_PASSWORD=ci-smoke-test-only \
  -v "$temp_dir/config:/app/config" "$image"
ready=false
for attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:5000/healthz; then
    ready=true
    break
  fi
  sleep 2
done
[[ "$ready" == true ]]
curl -fsSL http://127.0.0.1:5000/ | grep -q 'id="app"'
curl -fsS -c "$temp_dir/cookies" -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"ci-smoke-test-only"}' \
  http://127.0.0.1:5000/api/auth/login | python3 -c 'import json,sys; assert json.load(sys.stdin)["success"]'
docker restart "$container"
for attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:5000/healthz; then break; fi
  sleep 2
done
curl -fsS -b "$temp_dir/cookies" http://127.0.0.1:5000/api/auth/check \
  | python3 -c 'import json,sys; assert json.load(sys.stdin)["success"]'
echo 'PASS: startup, scheduler, UI, login, persisted session after restart'
