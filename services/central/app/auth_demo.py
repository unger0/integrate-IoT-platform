"""Autorização didática OPT-IN de API. NÃO é OIDC/OAuth, sem MFA, TLS ou login.

Valida tokens HS256 emitidos apenas para testes locais. Não usar em produção.
"""
import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import AsyncIterator

import jwt
from fastapi import Header, HTTPException, Request

ISSUER = 'iot-lab-local'
AUDIENCE = 'iot-api-local'
ROLES = {'administrador', 'gestor', 'integrador', 'operador', 'leitor', 'borda', 'dispositivo'}
_CURRENT: ContextVar['Principal | None'] = ContextVar('principal_do_lab', default=None)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    role: str
    device_id: str | None = None


def enabled() -> bool:
    return os.environ.get('IOT_LAB_AUTH_MODE', 'off') == 'jwt'


def validate_secret() -> str:
    secret = os.environ.get('IOT_LAB_JWT_SECRET', '')
    if len(secret.encode('utf-8')) < 32:
        raise RuntimeError('IOT_LAB_JWT_SECRET precisa ter pelo menos 32 bytes no modo jwt')
    return secret


def decode_token(token: str, secret: str) -> Principal:
    try:
        data = jwt.decode(
            token, secret, algorithms=['HS256'], issuer=ISSUER, audience=AUDIENCE,
            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub', 'tenant', 'role']},
            leeway=5,
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, 'token ausente, inválido ou expirado') from exc
    tenant = data.get('tenant')
    role = data.get('role')
    subject = data.get('sub')
    device_id = data.get('device_id')
    if not isinstance(tenant, str) or not tenant.strip() or role not in ROLES:
        raise HTTPException(401, 'claims de organização ou papel inválidas')
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(401, 'identidade inválida')
    if role == 'dispositivo' and (not isinstance(device_id, str) or not device_id.strip()):
        raise HTTPException(401, 'token de dispositivo sem dispositivo vinculado')
    return Principal(subject, tenant, role, device_id if isinstance(device_id, str) else None)


async def authenticate(request: Request, authorization: str | None = Header(default=None)) -> AsyncIterator[None]:
    if not enabled() or request.url.path == '/health':
        yield
        return
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Authorization: Bearer <token> obrigatório', headers={'WWW-Authenticate': 'Bearer'})
    principal = decode_token(authorization.removeprefix('Bearer ').strip(), validate_secret())
    marker = _CURRENT.set(principal)
    try:
        yield
    finally:
        _CURRENT.reset(marker)


def current() -> Principal | None:
    return _CURRENT.get() if enabled() else None


def require_roles(*allowed: str) -> Principal | None:
    if not enabled():
        return None
    principal = _CURRENT.get()
    if principal is None:
        raise HTTPException(401, 'não autenticado')
    if principal.role not in allowed:
        raise HTTPException(403, 'papel sem permissão para esta operação')
    return principal


def require_tenant(tenant: str, *allowed: str) -> Principal | None:
    principal = require_roles(*allowed)
    if principal is not None and principal.tenant != tenant:
        raise HTTPException(403, 'acesso negado a outra organização')
    return principal


def require_device(tenant: str, device_id: str, *allowed: str) -> Principal | None:
    principal = require_tenant(tenant, *allowed)
    if principal is not None and principal.role == 'dispositivo' and principal.device_id != device_id:
        raise HTTPException(403, 'dispositivo não autorizado para este identificador')
    return principal
