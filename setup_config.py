# SPDX-License-Identifier: Apache-2.0
"""Local configuration validation and atomic storage; never contacts ARCA."""
from core import DATA_ROOT
from domain import BillingEnvironment, Issuer
from security import safe_data_path, write_private_json


def validate_config(config):
    Issuer(str(config.get("cuit", "")), int(config.get("punto_venta", 0)), str(config.get("nombre_emisor", "")), BillingEnvironment(config.get("entorno", "homologacion")))
    for field, suffixes in [("certificado", {".crt", ".cer", ".pem"}), ("clave_privada", {".key", ".pem"})]:
        safe_data_path(DATA_ROOT, config.get(field, ""), suffixes)
    for field in ["nombre_emisor", "profesion", "descripcion_servicio", "domicilio_comercial", "localidad", "matricula", "alias", "cbu"]:
        value = config.get(field, "")
        if not isinstance(value, str) or len(value) > 500 or "\x00" in value:
            raise ValueError("Los datos del emisor admiten textos de hasta 500 caracteres")
    return config


def save_config(config):
    validate_config(config)
    write_private_json(DATA_ROOT, "config.json", config)
