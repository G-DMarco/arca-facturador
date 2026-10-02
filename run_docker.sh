#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v docker >/dev/null || ! docker info >/dev/null 2>&1; then
    printf '%s\n' 'Inicia Docker primero. / Start Docker first.' >&2
    exit 1
fi
docker compose up -d --build
printf '%s\n' 'Abre / Open: http://127.0.0.1:8501'
