# SPDX-License-Identifier: Apache-2.0
"""Local configuration validation and atomic storage; never contacts ARCA."""
import json
import os
import tempfile
from pathlib import Path

from core import DATA_ROOT, environment


def validate_config(config):
    environment(config)
    cuit = str(config.get("cuit", ""))
    if not cuit.isascii() or not cuit.isdigit() or len(cuit) != 11 or cuit == "00000000000":
        raise ValueError("Ingresá tu CUIT de 11 dígitos, sin guiones.")
    if not 1 <= int(config.get("punto_venta", 0)) <= 99999:
        raise ValueError("El punto de venta debe estar entre 1 y 99999.")
    if not str(config.get("nombre_emisor", "")).strip():
        raise ValueError("Ingresá el nombre del profesional.")
    for field in ("certificado", "clave_privada"):
        path = Path(config.get(field, ""))
        if not str(config.get(field, "")).strip() or path.is_absolute() or ".." in path.parts:
            raise ValueError("Las rutas del certificado y la clave deben estar dentro de la carpeta de datos.")
        if not (DATA_ROOT / path).resolve().is_relative_to(DATA_ROOT):
            raise ValueError("El certificado y la clave deben estar dentro de la carpeta de datos.")
    return config


def save_config(config):
    validate_config(config)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    path = DATA_ROOT / "config.json"
    descriptor, temporary = tempfile.mkstemp(prefix=".config-", dir=DATA_ROOT)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
