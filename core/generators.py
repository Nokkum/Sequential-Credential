import jwt
import time
from typing import Dict


def generate_jwt(payload: Dict, secret: str, expire_seconds: int = 3600) -> str:
    payload_copy = dict(payload)
    payload_copy['iat'] = int(time.time())
    payload_copy['exp'] = int(time.time()) + expire_seconds
    token = jwt.encode(payload_copy, secret, algorithm='HS256')
    return token


def github_app_jwt(app_id: str, private_key_pem: str, expire_seconds: int = 600) -> str:
    # For actual GitHub App JWTs, use PyJWT with RS256 and proper claims
    payload = {'iat': int(time.time()), 'exp': int(time.time()) + expire_seconds, 'iss': app_id}
    token = jwt.encode(payload, private_key_pem, algorithm='RS256')
    return token