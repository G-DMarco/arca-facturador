# SPDX-License-Identifier: Apache-2.0
"""Local configuration validation and atomic storage; never contacts ARCA."""
import json
import os
import tempfile
from pathlib import Path

from core import DATA_ROOT
from domain import BillingEnvironment, Issuer


def validate_config(config):
    Issuer(str(config.get("cuit", "")), int(config.get("punto_venta", 0)), str(config.get("nombre_emisor", "")), BillingEnvironment(config.get("entorno", "homologacion")))
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
