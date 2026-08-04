FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# MySQL-only by default. Set --build-arg INSTALL_ORACLE_CLIENT=true to also
# install the Oracle Instant Client (needed only for live Oracle reads).
ARG INSTALL_ORACLE_CLIENT=false

# MySQL client libs + build tools (mysqlclient). libaio1 kept for cx_Oracle import.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaio1 \
    default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Optional Oracle Instant Client (thick mode). Skipped for MySQL-only deploys.
RUN if [ "$INSTALL_ORACLE_CLIENT" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends wget unzip \
        && mkdir -p /opt/oracle \
        && wget -q https://download.oracle.com/otn_software/linux/instantclient/2340000/instantclient-basic-linux.x64-23.4.0.24.05.zip -O /tmp/ic.zip \
        && unzip -q /tmp/ic.zip -d /opt/oracle \
        && ln -s /opt/oracle/instantclient_23_4 /opt/oracle/instantclient \
        && rm -f /tmp/ic.zip \
        && apt-get purge -y wget unzip \
        && apt-get autoremove -y \
        && rm -rf /var/lib/apt/lists/*; \
    fi

COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
