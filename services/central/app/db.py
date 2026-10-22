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
-- Catálogo configurável de perfis para cada organização.
CREATE TABLE IF NOT EXISTS device_profiles (
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    expected_interval_seconds INTEGER NOT NULL CHECK (expected_interval_seconds > 0),
    PRIMARY KEY (tenant_id, name),
    FOREIGN KEY (tenant_id, domain) REFERENCES domains(tenant_id, name)
);
CREATE TABLE IF NOT EXISTS profile_measures (
    tenant_id TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    measurement_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    minimum DOUBLE PRECISION NOT NULL,
    maximum DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (tenant_id, profile_name, measurement_name),
    FOREIGN KEY (tenant_id, profile_name) REFERENCES device_profiles(tenant_id, name),
    CHECK (minimum <= maximum)
);
-- Migração aditiva: funciona sobre volumes PostgreSQL da versão 0.1.0.
ALTER TABLE devices ADD COLUMN IF NOT EXISTS profile_name TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS manufacturer TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS firmware TEXT;
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
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS quality TEXT NOT NULL DEFAULT 'nao_avaliada';
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS quality_reason TEXT;
CREATE INDEX IF NOT EXISTS measurements_time_idx ON measurements(device_id, measured_at DESC);
-- Regras de limite: vinculadas explicitamente ao dispositivo e à organização.
CREATE TABLE IF NOT EXISTS threshold_rules (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    device_id TEXT NOT NULL REFERENCES devices(id),
    measurement_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    operator TEXT NOT NULL CHECK (operator IN ('maior_que','menor_que')),
    threshold DOUBLE PRECISION NOT NULL CHECK (threshold > '-Infinity'::float8 AND threshold < 'Infinity'::float8),
    severity TEXT NOT NULL CHECK (severity IN ('baixa','media','alta','critica')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
CREATE INDEX IF NOT EXISTS threshold_rules_match_idx ON threshold_rules(device_id,measurement_name,enabled);
CREATE TABLE IF NOT EXISTS alarms (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT NOT NULL REFERENCES threshold_rules(id),
    device_id TEXT NOT NULL REFERENCES devices(id),
    tenant_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ativo','reconhecido','resolvido')),
    initial_value DOUBLE PRECISION NOT NULL,
    last_value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    occurrences INTEGER NOT NULL DEFAULT 1,
    first_measured_at TIMESTAMPTZ NOT NULL,
    last_measured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolved_reason TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS alarms_open_unique_idx ON alarms(rule_id,device_id)
    WHERE status IN ('ativo','reconhecido');
CREATE INDEX IF NOT EXISTS alarms_tenant_time_idx ON alarms(tenant_id,created_at DESC);
CREATE TABLE IF NOT EXISTS alarm_events (
    id BIGSERIAL PRIMARY KEY,
    alarm_id BIGINT NOT NULL REFERENCES alarms(id),
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS last_state (
    device_id TEXT NOT NULL,
    measurement_name TEXT NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (device_id, measurement_name)
);
"""

# Mudanças aditivas também para a tabela last_state, que já podia existir.
MIGRATIONS = [
    "ALTER TABLE last_state ADD COLUMN IF NOT EXISTS quality TEXT NOT NULL DEFAULT 'nao_avaliada'",
    "ALTER TABLE last_state ADD COLUMN IF NOT EXISTS quality_reason TEXT",
]

def initialize():
    with connection() as conn:
        for statement in SCHEMA.split(';'):
            if statement.strip():
                conn.execute(statement)
        for statement in MIGRATIONS:
            conn.execute(statement)
