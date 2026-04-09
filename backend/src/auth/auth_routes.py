from typing import Annotated
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from .service import AuthService
from src.db.main import get_session
from .utils import verify_passwd, seconds_until_expiry
from datetime import datetime, timezone
from .dependencies import (
    RefreshTokenBearer,
    access_token_bearer,
    require_user,
)
from src.db.redis_client import (
    add_jti_to_blocklist,
    store_refresh_token,
    get_refresh_token_owner,
    delete_refresh_token,
    revoke_all_user_refresh_tokens,
    get_user,
    add_registered_user,
)
from src.db.db_models import RegisterUserModel, LoginUserModel, UserDataModel
from .schemas import AccessTokenUserData, LoginResultEnum

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/signup", response_model=UserDataModel, status_code=status.HTTP_201_CREATED
)
async def create_user(
    user_data: RegisterUserModel,
    session: SessionDependency,
) -> UserDataModel:
    if not user_data.email:
        user_data.email = None
    if not user_data.nickname:
        user_data.nickname = None
    if not user_data.request:
        user_data.request = None

    if (
        await auth_service.username_exists(user_data.username, session)
        != LoginResultEnum.DNE
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User with that username already exists",
        )

    if user_data.email is not None:
        if (
            await auth_service.email_exists(user_data.email, session)
            != LoginResultEnum.DNE
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User with that email already exists",
            )

    return await auth_service.register_user(user_data, session)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(
    login_data: LoginUserModel,
    session: SessionDependency,
    response: Response,
):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    user = await auth_service.get_user_with_username(login_data.username, session)
    if user is None or not verify_passwd(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid username and/or password",
        )

    # Ensure the user is cached in Redis
    if not await get_user(user.username):
        await add_registered_user(user.username, user.role)

    access_token, refresh_token = await auth_service.generate_tokens(user)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # set True in production (requires HTTPS)
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return {
        "message": "login successful",
        "user": {
            "user_id": str(user.user_id),
            "username": user.username,
            "nickname": user.nickname,
            "role": user.role,
        },
    }


@router.post("/refresh_token")
async def rotate_refresh_token(
    response: Response,
    token_details: dict = Depends(RefreshTokenBearer()),
    session: SessionDependency = None,
):
    """
    POST /auth/refresh_token
    Issues a new access + refresh token pair and rotates the refresh token.

    Rotation rules:
    - The incoming refresh JTI must exist in the Redis refresh store.
    - If the JTI is NOT in the store (already rotated / never issued by us),
      this is a reuse attack: revoke every refresh token for this user and
      force re-login.
    - The old JTI is deleted from the store and blocklisted.
    - A brand-new pair is issued and the new refresh JTI is stored.
    """
    if datetime.fromtimestamp(token_details["exp"], tz=timezone.utc) <= datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired"
        )

    jti = token_details["jti"]
    username = token_details["user"]["username"]

    owner = await get_refresh_token_owner(jti)

    if owner is None:
        # Token not in store — either reuse of an already-rotated token
        # or a forged token that was never stored. Revoke everything.
        await revoke_all_user_refresh_tokens(username)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions revoked. Please log in again.",
        )

    if owner != username:
        # JTI exists but belongs to a different user — should never happen
        # with valid tokens, treat as tampering.
        await delete_refresh_token(jti)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Rotate: remove old JTI from store + blocklist it, issue fresh pair
    await delete_refresh_token(jti)
    ttl = seconds_until_expiry(token_details)
    await add_jti_to_blocklist(jti, max(ttl, 1))

    user = await auth_service.get_user_with_username(username, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )

    access_token, new_refresh_token = await auth_service.generate_tokens(user)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return {"message": "tokens rotated"}


@router.get("/me")
async def get_current_user(
    session: SessionDependency,
    token_details: dict = require_user,
):
    """
    GET /auth/me
    Returns the full User record for the authenticated caller, including
    the live role. The frontend should source role from here, not the token.
    """
    username = token_details["user"]["username"]
    user = await auth_service.get_user_with_username(username, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post("/logout")
async def revoke_token(
    response: Response,
    token_details: dict = access_token_bearer,
):
    """
    POST /auth/logout
    Blocklists the access token JTI, revokes all refresh tokens for the user,
    and deletes both cookies from the browser.
    """
    jti = token_details["jti"]
    username = token_details["user"]["username"]

    ttl = seconds_until_expiry(token_details)
    await add_jti_to_blocklist(jti, max(ttl, 1))
    await revoke_all_user_refresh_tokens(username)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {"message": "Logged out successfully"}
