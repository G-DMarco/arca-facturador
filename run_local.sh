#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
umask 077
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -x .venv/bin/python ]]; then
    python_bin=.venv/bin/python
elif [[ -x .venv/Scripts/python.exe ]]; then
    python_bin=.venv/Scripts/python.exe
else
    printf '%s\n' 'Create .venv and install requirements.txt first. / Primero crea .venv e instala requirements.txt.' >&2
    exit 1
fi
if [[ $# -gt 0 ]]; then
    printf '%s\n' 'Usage / Uso: bash run_local.sh (no arguments / sin argumentos)' >&2
    exit 1
fi
exec "$python_bin" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
