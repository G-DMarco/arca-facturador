# SPDX-License-Identifier: Apache-2.0
"""Input and private-storage boundaries, independent of the user interface."""
import json
import os
import tempfile
from pathlib import Path, PureWindowsPath

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_BATCH_ROWS = 500
MAX_FIELD_CHARS = 2000


def safe_data_path(root, value, suffixes=None):
    if not isinstance(value, str) or not value or len(value) > 240 or any(c in value for c in ("\x00", "\n", "\r")):
        raise ValueError("Ruta privada inválida")
    normalized = value.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute() or PureWindowsPath(value).drive or ".." in path.parts:
        raise ValueError("La ruta debe estar dentro de la carpeta de datos")
    root = Path(root).resolve()
    candidate = root / path
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
        raise ValueError("No se permiten enlaces ni rutas fuera de la carpeta de datos")
    if suffixes and candidate.suffix.lower() not in suffixes:
        raise ValueError("Formato de archivo privado no permitido")
    return candidate


def private_file(root, name):
    path = safe_data_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    os.close(descriptor)
    if os.name != "nt":
        path.chmod(0o600)
    return path


def write_private_json(root, name, payload):
    path = safe_data_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".private-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_fields(row):
    for field, value in row.items():
        if not isinstance(value, str) or len(value) > MAX_FIELD_CHARS or "\x00" in value:
            raise ValueError("Campo CSV inválido o demasiado largo")
        # A CSV exported later must not execute spreadsheet formulas.
        if field in {"id", "nombre", "observaciones", "nota"} and value.lstrip().startswith(("=", "+", "-", "@")):
            raise ValueError("Los textos del CSV no pueden comenzar con =, +, - o @")
