"""Emite SOMENTE tokens de laboratório HS256; não implementa OAuth/OIDC.

Em modo demonstrativo, mantenha a chave e os tokens fora do Git.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import time
import uuid


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def mint(secret: str, subject: str, tenant: str, role: str, ttl: int, device: str | None = None) -> str:
    if len(secret.encode('utf-8')) < 32:
        raise ValueError('chave insuficiente; exigidos pelo menos 32 bytes')
    now = int(time.time())
    payload = {'iss':'iot-lab-local', 'aud':'iot-api-local', 'sub':subject, 'tenant':tenant,
               'role':role, 'iat':now, 'exp':now+ttl, 'jti':str(uuid.uuid4())}
    if device:
        payload['device_id'] = device
    head = b64(json.dumps({'typ':'JWT','alg':'HS256'},separators=(',',':')).encode())
    body = b64(json.dumps(payload,separators=(',',':')).encode())
    sig = b64(hmac.new(secret.encode(), f'{head}.{body}'.encode(), hashlib.sha256).digest())
    return f'{head}.{body}.{sig}'


if __name__ == '__main__':
    p=argparse.ArgumentParser(description='Apenas laboratório. Não usar em sistemas reais.')
    p.add_argument('--inquilino', default='coop-cerrado')
    p.add_argument('--papel', choices=['administrador','gestor','integrador','operador','leitor','borda','dispositivo'],default='gestor')
    p.add_argument('--sujeito', default='estudante-demo')
    p.add_argument('--dispositivo',default=None)
    p.add_argument('--segundos',type=int,default=3600)
    args=p.parse_args()
    if args.segundos < 1 or args.segundos > 86400:
        p.error('Validade aceita no laboratório: 1 até 86400 segundos')
    if args.papel=='dispositivo' and not args.dispositivo:
        p.error('Token do papel dispositivo exige --dispositivo')
    secret=os.environ.get('IOT_LAB_JWT_SECRET','')
    print(mint(secret,args.sujeito,args.inquilino,args.papel,args.segundos,args.dispositivo))
