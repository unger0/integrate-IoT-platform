import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://iot_lab:iot_lab_nao_producao@localhost:5432/iot_laboratorio')

def connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (tenant_id, name)
);
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    site TEXT NOT NULL,
    area TEXT
);
CREATE TABLE IF NOT EXISTS telemetry_messages (
    message_id UUID PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES devices(id),
    tenant_id TEXT NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS measurements (
    message_id UUID NOT NULL REFERENCES telemetry_messages(message_id),
    ordinal INT NOT NULL,
    device_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    measurement_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (message_id, ordinal)
);
CREATE INDEX IF NOT EXISTS measurements_time_idx ON measurements(device_id, measured_at DESC);
CREATE TABLE IF NOT EXISTS last_state (
    device_id TEXT NOT NULL,
    measurement_name TEXT NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (device_id, measurement_name)
);
"""

def initialize():
    with connection() as conn:
        for statement in SCHEMA.split(';'):
            if statement.strip():
                conn.execute(statement)
