from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.config import settings
from typing import Optional


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_id_from_token(token: str) -> Optional[int]:
    payload = verify_token(token)
    return payload.get("userId") or payload.get("sub")
