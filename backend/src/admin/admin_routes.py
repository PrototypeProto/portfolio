from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Body, status
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from .service import AdminService
from src.auth.service import AuthService
from src.db.main import get_session
from src.auth.dependencies import require_admin
from src.db.db_models import MemberRoleEnum
from src.db.read_models import *

router = APIRouter(prefix="/admin", tags=["admin"])
admin_service = AdminService()
auth_service = AuthService()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/users", response_model=List[UserRead])
async def get_verified_users(
    session: SessionDependency,
    token_details: dict = require_admin,
):
    """
    GET /admin/users
    Lists all verified users for the admin panel.
    NOTE: exclude self when modifying user values to avoid conflicts
    like accidentally demoting yourself.
    """
    return await admin_service.get_users(session)


@router.get("/users/pending", response_model=List[PendingUserRead])
async def get_pending_users(
    session: SessionDependency,
    token_details: dict = require_admin,
):
    """
    GET /admin/users/pending
    Lists all pending users for the admin approval panel.
    """
    return await admin_service.get_pending_users(session)


@router.get("/users/stats", response_model=UserStats)
async def get_user_stats(
    session: SessionDependency,
    token_details: dict = require_admin,
):
    """
    GET /admin/users/stats
    Returns verified/vip/admin/pending user counts.
    """
    return await admin_service.get_user_stats(session)


@router.patch("/users/{username}/role")
async def update_user_role(
    username: str,
    session: SessionDependency,
    token_details: dict = require_admin,
    role: MemberRoleEnum = Body(..., embed=True),
):
    """
    PATCH /admin/users/{username}/role  { role }
    Updates a verified user's site role.
    """
    if not await admin_service.is_verified_user(username, session):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist"
        )

    res = await admin_service.update_user_role(username, role, session)
    if res is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role",
        )


@router.post("/users/{username}/approve", response_model=UserRead)
async def approve_pending_user(
    username: str,
    session: SessionDependency,
    token_details: dict = require_admin,
):
    """
    POST /admin/users/{username}/approve
    Moves a pending user to the verified user table.
    """
    if await admin_service.is_verified_user(username, session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already verified",
        )

    try:
        new_user = await admin_service.approve_pending_user(username, session)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to approve user",
        )

    if new_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pending user not found"
        )

    return new_user


@router.post("/users/{username}/reject", response_model=RejectedUserRead)
async def reject_pending_user(
    username: str,
    session: SessionDependency,
    token_details: dict = require_admin,
):
    """
    POST /admin/users/{username}/reject
    Copies the pending user to rejected_user and removes the pending entry.
    """
    if await admin_service.is_verified_user(username, session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already verified",
        )

    try:
        rejected = await admin_service.reject_pending_user(username, session)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to reject user"
        )

    if rejected is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pending user not found"
        )

    return rejected
