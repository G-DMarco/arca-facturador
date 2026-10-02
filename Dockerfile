# SPDX-License-Identifier: Apache-2.0
FROM python:3.13-slim@sha256:bb2988715db2cf7ace7b53f38f3cffbef7c7046a656bee66245eb0ed386e2e81
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ARCA_DATA_DIR=/data HOME=/tmp
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock     && groupadd --gid 10001 arca     && useradd --uid 10001 --gid arca --no-create-home arca     && mkdir -p /data/certificados     && chown -R arca:arca /data
COPY app.py core.py domain.py security.py generate_invoice_pdf.py setup_config.py ./
COPY config.example.json config.produccion.example.json facturas_ejemplo.csv LICENSE NOTICE ./
COPY .streamlit/config.toml .streamlit/config.toml
USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
ENTRYPOINT ["/bin/sh", "-c", "umask 077; exec python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --browser.gatherUsageStats false"]
