from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

class Medida(BaseModel):
    model_config = ConfigDict(extra='forbid')
    grandeza: str = Field(min_length=1)
    valor: float = Field(allow_inf_nan=False)
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
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    inquilino: str = Field(min_length=1)
    dominio: str = Field(min_length=1)
    site: str = Field(min_length=1)
    area: str | None = None
    perfil: str | None = None
    fabricante: str | None = None
    firmware: str | None = None

class NovoDominio(BaseModel):
    inquilino: str = Field(min_length=1)
    nome: str = Field(min_length=1)


class GrandezaPerfil(BaseModel):
    """Parâmetros de uma grandeza, configurados por organização."""
    model_config = ConfigDict(extra='forbid')
    grandeza: str = Field(min_length=1)
    unidade: str = Field(min_length=1)
    minimo: float = Field(allow_inf_nan=False)
    maximo: float = Field(allow_inf_nan=False)

    @model_validator(mode='after')
    def validate_range(self):
        if self.minimo > self.maximo:
            raise ValueError('minimo não pode ser maior que maximo')
        return self


class NovoPerfil(BaseModel):
    model_config = ConfigDict(extra='forbid')
    inquilino: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    dominio: str = Field(min_length=1)
    intervalo_esperado_segundos: int = Field(ge=1, le=2_592_000)
    medidas: list[GrandezaPerfil] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def validate_unique_measurements(self):
        nomes = [item.grandeza for item in self.medidas]
        if len(nomes) != len(set(nomes)):
            raise ValueError('grandezas não podem se repetir no perfil')
        return self


class VinculoPerfil(BaseModel):
    model_config = ConfigDict(extra='forbid')
    inquilino: str = Field(min_length=1)
    perfil: str = Field(min_length=1)
