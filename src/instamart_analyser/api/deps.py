"""Auth dependencies for viewer / reviewer / admin roles."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from instamart_analyser.api.schemas.models import RoleName, TokenUser
from instamart_analyser.common.config import (
    API_ADMIN_TOKEN,
    API_REVIEWER_TOKEN,
    API_VIEWER_TOKEN,
)

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_RANK = {"viewer": 1, "reviewer": 2, "admin": 3}


def _resolve_user(token: str | None) -> TokenUser:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token. Use Authorization: Bearer <token>",
        )
    mapping = {
        API_VIEWER_TOKEN: TokenUser(role="viewer", token_name="viewer"),
        API_REVIEWER_TOKEN: TokenUser(role="reviewer", token_name="reviewer"),
        API_ADMIN_TOKEN: TokenUser(role="admin", token_name="admin"),
    }
    user = mapping.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> TokenUser:
    token = credentials.credentials if credentials else None
    return _resolve_user(token)


def require_role(minimum: RoleName):
    def dependency(user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum}' or higher",
            )
        return user

    return dependency
