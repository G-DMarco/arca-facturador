# SPDX-License-Identifier: Apache-2.0
"""Facturas C, ARS, servicios, DNI: homologación y producción."""
import base64
import csv
import io
import json
import os
import ssl
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from filelock import FileLock
from domain import Authorization, BillingPeriod, Customer, InvoiceDraft, InvoiceState, ServiceItem

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("ARCA_DATA_DIR", str(ROOT))).resolve()
ENVIRONMENTS = {
    'homologacion': {
        'scope': 'homo',
        'db': 'homologacion.sqlite3',
        'lock': 'emision_homologacion.lock',
        'ta_cache': 'wsaa_ta_homologacion.json',
        'wsaa': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL',
        'wsfe': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL',
        'pdf_label': 'PRUEBA DE HOMOLOGACION - SIN VALIDEZ FISCAL',
    },
    'produccion': {
        'scope': 'prod',
        'db': 'produccion.sqlite3',
        'lock': 'emision_produccion.lock',
        'ta_cache': 'wsaa_ta_produccion.json',
        'wsaa': 'https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL',
        'wsfe': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL',
        'pdf_label': 'FACTURA ELECTRONICA',
    },
}


def environment(config):
    name = config.get('entorno', 'homologacion')
    if name not in ENVIRONMENTS:
        raise ValueError("entorno debe ser 'homologacion' o 'produccion'")
    return name, ENVIRONMENTS[name]


def soap_transport(env_name):
    from requests import Session
    from requests.adapters import HTTPAdapter
    from urllib3.poolmanager import PoolManager
    from zeep.transports import Transport

    class LegacyTLSAdapter(HTTPAdapter):
        def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
            context = ssl.create_default_context()
            context.set_ciphers('DEFAULT:@SECLEVEL=1')
            pool_kwargs['ssl_context'] = context
            return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    session = Session()
    if env_name == 'produccion':
        session.mount('https://', LegacyTLSAdapter())
    return Transport(session=session, timeout=30, operation_timeout=45)

def parse_csv(data):
    if not data.strip():
        raise ValueError('CSV vacío')
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')), delimiter=';' if ';' in data.decode('utf-8-sig').splitlines()[0] else ',')
    rows, ids = [], set()
    required = {'id','nombre','documento','fecha','desde','hasta','vencimiento','sesiones','precio_sesion','condicion_iva'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Faltan columnas: ' + ', '.join(sorted(required-set(reader.fieldnames or []))))
    for line, row in enumerate(reader, 2):
        row = {k: v.strip() if v else '' for k,v in row.items() if k}
        try:
            if not row['id'] or row['id'] in ids:
                raise ValueError('ID vacío/duplicado')
            ids.add(row['id'])
            dates = {key: datetime.strptime(row[key], "%Y-%m-%d").date() for key in ("fecha", "desde", "hasta", "vencimiento")}
            quantity = int(row["sesiones"])
            description = row.get("observaciones") or f"{quantity} unidades de servicio. Cliente: {row['nombre']}. Período: {row['desde']} a {row['hasta']}."
            draft = InvoiceDraft(
                row["id"],
                Customer(row["nombre"], row["documento"], int(row["condicion_iva"])),
                ServiceItem(description, quantity, Decimal(row["precio_sesion"].replace(",", "."))),
                BillingPeriod(dates["fecha"], dates["desde"], dates["hasta"], dates["vencimiento"]),
            )
            row['total'] = str(draft.total)
            row['descripcion'] = draft.service.description
            rows.append(row)
        except (ValueError, InvalidOperation) as e:
            raise ValueError(f'Fila {line}: {e}') from e
    if not rows:
        raise ValueError('CSV sin facturas')
    return rows

class Arca:
    def __init__(self, config):
        from zeep import Client
        self.c = config
        self.env_name, self.env = environment(config)
        if not str(config['cuit']).isdigit() or len(str(config['cuit'])) != 11 or int(config['punto_venta']) <= 0:
            raise ValueError('CUIT/punto de venta inválido')
        transport = soap_transport(self.env_name)
        self.auth = self._cached_auth(config)
        if not self.auth:
            cert = x509.load_pem_x509_certificate((DATA_ROOT/config['certificado']).read_bytes())
            key = serialization.load_pem_private_key((DATA_ROOT/config['clave_privada']).read_bytes(), password=None)
            now = datetime.now(timezone.utc)
            ticket = ET.Element('loginTicketRequest', version='1.0')
            header = ET.SubElement(ticket, 'header')
            for tag,value in [('uniqueId',str(int(time.time()))), ('generationTime',(now-timedelta(minutes=5)).isoformat()), ('expirationTime',(now+timedelta(hours=1)).isoformat())]:
                ET.SubElement(header,tag).text = value
            ET.SubElement(ticket,'service').text = 'wsfe'
            cms = pkcs7.PKCS7SignatureBuilder().set_data(ET.tostring(ticket)).add_signer(cert,key,hashes.SHA256()).sign(serialization.Encoding.DER,[pkcs7.PKCS7Options.Binary])
            wsaa = Client(self.env['wsaa'], transport=transport)
            reply = ET.fromstring(wsaa.service.loginCms(base64.b64encode(cms).decode()))
            self.auth = {'Token':reply.findtext('.//token'),'Sign':reply.findtext('.//sign'),'Cuit':int(config['cuit'])}
            self._save_auth(config, reply)
        self.ws = Client(self.env['wsfe'], transport=transport)

    def _cached_auth(self, config):
        try:
            data = json.loads((DATA_ROOT/self.env['ta_cache']).read_text(encoding='utf-8'))
            expires = datetime.fromisoformat(data['expiration_time'])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if data.get('cuit') == str(config['cuit']) and data.get('entorno') == self.env_name and data.get('service') == 'wsfe' and expires > datetime.now(timezone.utc) + timedelta(minutes=5):
                return {'Token':data['token'],'Sign':data['sign'],'Cuit':int(config['cuit'])}
        except Exception:
            return None
        return None

    def _save_auth(self, config, reply):
        expiration = reply.findtext('.//expirationTime')
        payload = {
            'cuit': str(config['cuit']),
            'entorno': self.env_name,
            'service': 'wsfe',
            'token': self.auth['Token'],
            'sign': self.auth['Sign'],
            'expiration_time': expiration,
        }
        (DATA_ROOT/self.env['ta_cache']).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def query(self, number):
        from zeep.helpers import serialize_object
        return serialize_object(self.ws.service.FECompConsultar(Auth=self.auth,FeCompConsReq={'CbteTipo':11,'CbteNro':number,'PtoVta':int(self.c['punto_venta'])}))

    def points_of_sale(self):
        from zeep.helpers import serialize_object
        return serialize_object(self.ws.service.FEParamGetPtosVenta(Auth=self.auth))

    def issue(self, row, number):
        from zeep.helpers import serialize_object
        date = lambda key: row[key].replace('-','')
        doc_tipo = 96 if row['documento'] else 99
        doc_nro = int(row['documento']) if row['documento'] else 0
        detail = dict(Concepto=2,DocTipo=doc_tipo,DocNro=doc_nro,CbteDesde=number,CbteHasta=number,CbteFch=date('fecha'),ImpTotal=Decimal(row['total']),ImpTotConc=0,ImpNeto=Decimal(row['total']),ImpOpEx=0,ImpTrib=0,ImpIVA=0,FchServDesde=date('desde'),FchServHasta=date('hasta'),FchVtoPago=date('vencimiento'),MonId='PES',MonCotiz=1,CondicionIVAReceptorId=5)
        return serialize_object(self.ws.service.FECAESolicitar(Auth=self.auth,FeCAEReq={'FeCabReq':{'CantReg':1,'PtoVta':int(self.c['punto_venta']),'CbteTipo':11},'FeDetReq':{'FECAEDetRequest':[detail]}}))

def emit_batch(rows, config):
    """Reserva persistente antes del envío. Nunca reenvía estados inciertos."""
    output = []
    env_name, env = environment(config)
    with FileLock(str(DATA_ROOT/env['lock']), timeout=1):
        db = sqlite3.connect(DATA_ROOT/env['db'])
        try:
            db.execute('CREATE TABLE IF NOT EXISTS facturas (scope TEXT, id TEXT, payload TEXT, numero INTEGER, estado TEXT, respuesta TEXT, PRIMARY KEY(scope,id))')
            scope = f"{env['scope']}:{config['cuit']}:{config['punto_venta']}"
            pending = db.execute("SELECT id,numero FROM facturas WHERE scope=? AND estado='pendiente'",(scope,)).fetchall()
            if pending:
                raise ValueError(f'Hay emisiones inciertas {pending}. Consultar ARCA y conciliar antes de continuar; no se reenvían automáticamente.')
            rows_to_issue = []
            for row in rows:
                payload = json.dumps(row,ensure_ascii=False,sort_keys=True)
                old = db.execute('SELECT payload,numero,estado,respuesta FROM facturas WHERE scope=? AND id=?',(scope,row['id'])).fetchone()
                if old:
                    if old[0] != payload:
                        raise ValueError(f"ID {row['id']} ya registrado con datos distintos")
                    if InvoiceState(old[2]).allows_retry:
                        rows_to_issue.append((row, payload))
                        continue
                    output.append({'id':row['id'],'numero':old[1],'estado':old[2],'respuesta':json.loads(old[3]) if old[3] else None})
                    continue
                rows_to_issue.append((row, payload))
            if not rows_to_issue:
                return output
            api = Arca(config)
            last = api.ws.service.FECompUltimoAutorizado(Auth=api.auth,PtoVta=int(config['punto_venta']),CbteTipo=11)
            if last.Errors:
                raise ValueError(str(last.Errors))
            number = int(last.CbteNro)
            for row, payload in rows_to_issue:
                number += 1
                db.execute('INSERT OR REPLACE INTO facturas VALUES (?,?,?,?,?,?)',(scope,row['id'],payload,number,'pendiente',None))
                db.commit()
                response = api.issue(row,number)
                authorization = Authorization.from_response(response)
                accepted = authorization.state is InvoiceState.AUTHORIZED
                state = authorization.state.value
                db.execute('UPDATE facturas SET estado=?,respuesta=? WHERE scope=? AND id=?',(state,json.dumps(response,default=str),scope,row['id']))
                db.commit()
                output.append({'id':row['id'],'numero':number,'estado':state,'respuesta':response})
                if not accepted:
                    break
            return output
        finally:
            db.close()

def get_points_of_sale(config):
    return Arca(config).points_of_sale()

def test_pdf(row, result, config):
    from generate_invoice_pdf import invoice_pdf
    return invoice_pdf(row, result, config)
