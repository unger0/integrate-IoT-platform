from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

class Medida(BaseModel):
    model_config = ConfigDict(extra='forbid')
    grandeza: str = Field(min_length=1)
    valor: float
    unidade: str = Field(min_length=1)

class Local(BaseModel):
    model_config = ConfigDict(extra='forbid')
    site: str | None = None
    area: str | None = None
    geo: dict | None = None  # validar contra GeoJSON na implementação definitiva

class Telemetria(BaseModel):
    model_config = ConfigDict(extra='forbid')
    versao: Literal['1.0']
    id_mensagem: UUID
    dispositivo: str = Field(min_length=1)
    tipo: Literal['telemetria']
    timestamp: datetime
    via: str | None = None
    local: Local | None = None
    medidas: list[Medida] = Field(min_length=1, max_length=100)

    @field_validator('timestamp')
    @classmethod
    def require_timezone(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('timestamp deve conter fuso horário (UTC recomendado)')
        return value

class NovoDispositivo(BaseModel):
    id: str = Field(min_length=1)
    inquilino: str = Field(min_length=1)
    dominio: str = Field(min_length=1)
    site: str = Field(min_length=1)
    area: str | None = None

class NovoDominio(BaseModel):
    inquilino: str = Field(min_length=1)
    nome: str = Field(min_length=1)
