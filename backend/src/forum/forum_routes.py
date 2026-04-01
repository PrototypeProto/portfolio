from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Session, select, func
from typing import Optional, Annotated
from datetime import datetime
from .service import ForumService
from src.db.read_models import *
from src.admin.service import AdminService
from src.db.models import User
from src.auth.dependencies import access_token_bearer
from src.auth.service import AuthService
from src.db.main import get_session

router = APIRouter(prefix="/forum", tags=["forum"], dependencies=[access_token_bearer])
service = ForumService()
auth_service = AuthService()
admin_service = AdminService()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]

# TOPIC GROUPS

@router.get("/groups", response_model=list[TopicGroupRead])
async def list_topic_groups(session: SessionDependency):
    """Get all topic groups ordered by display_order. Used to render the forum index."""
    return await service.get_topic_groups(session)


# TOPICS

@router.get("/topics", response_model=list[TopicRead])
async def list_topics(
    session: SessionDependency,
    group_id: Optional[UUID] = Query(None),
):
    """
    List all topics, optionally filtered by group.
    Returns thread/reply counts and last activity for the forum index sidebar.
    """
    return await service.retrieve_topics(group_id, session)


@router.get("/topics/{topic_id}", response_model=TopicRead)
async def get_topic(topic_id: UUID, session: SessionDependency):
    topic = await service.get_topic(topic_id, session)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


# NOTE: ADMIN ONLY
@router.post("/topics", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
async def create_topic(
    payload: TopicCreate,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await admin_service.verify_admin(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    return await service.create_topic(payload, session)


# NOTE: ADMIN ONLY
@router.patch("/topics/{topic_id}", response_model=TopicRead)
async def update_topic(
    topic_id: UUID,
    payload: TopicUpdate,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await admin_service.verify_admin(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    return await service.update_topic(topic_id, payload, session)


@router.patch("/topics/{topic_id}/lock", response_model=TopicRead)
async def toggle_topic_lock(
    topic_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """Lock or unlock a topic (prevents new threads from being created)."""
    if not await admin_service.verify_admin(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    return await service.toggle_topic_lock(topic_id, session)


# THREADS

@router.get("/topics/{topic_id}/threads", response_model=PaginatedThreads)
async def list_threads(
    topic_id: UUID,
    session: SessionDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("latest", regex="^(latest|top|oldest)$"),
):
    """
    Paginated thread listing for a topic.
    Pinned threads always float to the top regardless of sort.
    sort options: 'latest' (by created_at desc), 'top' (by upvotes), 'oldest'
    """
    topic = await service.get_topic(topic_id, session)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return await service.get_threads(topic_id, page, page_size, sort, session)

# Missing is_deleted from ThreadRead
@router.get("/threads/{thread_id}", response_model=ThreadRead)
async def get_thread(thread_id: UUID, session: SessionDependency):
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post(
    "/topics/{topic_id}/threads",
    response_model=ThreadRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_thread(
    topic_id: UUID,
    payload: ThreadCreate,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
    topic = await service.get_topic(topic_id, session)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.is_locked:
        raise HTTPException(status_code=403, detail="Topic is locked")

    author_id = token_details['user']['user_id']
    return await service.create_thread(topic_id, author_id, payload, session)


@router.patch("/threads/{thread_id}", response_model=ThreadRead)
async def update_thread(
    thread_id: UUID,
    payload: ThreadUpdate,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """Author or mod can edit. Only mods can change is_pinned / is_locked."""
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
    
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_id = token_details['user']['user_id']
    is_author = thread.author_id == user_id
    is_admin = admin_service.is_user_admin(token_details['user']['username'])

    if not is_author and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    # only mods may change pin/lock
    mod_only_fields = {"is_pinned", "pin_expires_at", "is_locked"}
    if any(f in payload.model_dump(exclude_unset=True) for f in mod_only_fields) and not is_admin:
        raise HTTPException(status_code=403, detail="Only moderators can pin or lock threads")

    return await service.update_thread(thread, payload, session)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """Soft-delete. Author or mod only."""
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
    
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_id = UUID(token_details["user"]['user_id'])
    is_author = thread.author_id == user_id
    is_admin = await admin_service.verify_admin(token_details, session)
    if not is_author and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    await service.delete_thread(thread, session)

# NOTE: service?
@router.patch("/threads/{thread_id}/lock", response_model=ThreadRead)
async def toggle_thread_lock(
    thread_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """Admin only."""
    if not await admin_service.verify_admin(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return await service.toggle_thread_lock(thread, session)


# admin : service?
@router.patch("/threads/{thread_id}/pin", response_model=ThreadRead)
async def toggle_thread_pin(
    thread_id: UUID,
    session: SessionDependency,
    pin_expires_at: Optional[datetime] = None,
    token_details: dict = access_token_bearer,
):
    """Admin only."""
    if not await admin_service.verify_admin(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")
    
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return await service.toggle_thread_pin(thread, pin_expires_at, session)


# THREAD VOTES

@router.post("/threads/{thread_id}/vote", response_model=VoteResult)
async def vote_thread(
    thread_id: UUID,
    payload: VotePayload,           # { is_upvote: bool }
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """
    Cast or flip a vote. Casting the same vote twice removes it (toggle).
    Returns updated up/downvote counts.
    """
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
    
    thread = await service.get_thread(thread, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_id = UUID(token_details["user"]['user_id'])
    return await service.vote_thread(thread, user_id, payload, session)
    


@router.get("/threads/{thread_id}/vote", response_model=Optional[VotePayload])
async def get_my_thread_vote(
    thread_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """Returns the current user's vote state on a thread (for rendering vote buttons)."""
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    user_id = UUID(token_details["user"]['user_id'])
    return await service.get_user_thread_vote(thread_id, user_id, session)


# REPLIES

@router.get("/threads/{thread_id}/replies", response_model=bool) #ReplyListResponse
async def list_replies(
    thread_id: UUID,
    session: SessionDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    token_details: dict = access_token_bearer,
):
    """
    Paginated top-level replies for a thread (parent_reply_id IS NULL).
    Nested replies are fetched separately per parent via /replies/{reply_id}/children.
    """
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
    
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return await service.get_replies(thread_id, page, page_size, session)


@router.get("/replies/{reply_id}/children", response_model=list[ReplyRead])
async def get_reply_children(
    reply_id: UUID,
    session: SessionDependency,
):
    """Fetch nested replies for a given parent reply (one level at a time)."""
    return await service.get_reply_children(reply_id, session)


@router.get("/replies/{reply_id}", response_model=ReplyRead)
async def get_reply(reply_id: UUID, session: SessionDependency):
    reply = await service.get_reply(reply_id, session)
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    return reply


@router.post(
    "/threads/{thread_id}/replies",
    response_model=ReplyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reply(
    thread_id: UUID,
    payload: ReplyCreate,          # { body, parent_reply_id? }
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    thread = await service.get_thread(thread_id, session)
    if not thread or thread.is_deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.is_locked:
        raise HTTPException(status_code=403, detail="Thread is locked")
 
    if payload.parent_reply_id:
        parent = await service.get_reply(payload.parent_reply_id, session)
        if not parent or parent.thread_id != thread_id:
            raise HTTPException(status_code=400, detail="Invalid parent reply")
 
    author_id = UUID(token_details["user"]['user_id'])
    return await service.create_reply(thread_id, author_id, payload, session)


@router.patch("/replies/{reply_id}", response_model=ReplyRead)
async def update_reply(
    reply_id: UUID,
    payload: ReplyUpdate,           # { body }
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    reply = await service.get_reply(reply_id, session)
    if not reply or reply.is_deleted:
        raise HTTPException(status_code=404, detail="Reply not found")
 
    user_id = UUID(token_details["user"]['user_id'])
    if reply.author_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
 
    return await service.update_reply(reply, payload, session)


@router.delete("/replies/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reply(
    reply_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """
    Soft-delete. Sets is_deleted=True but keeps the row so nested
    replies maintain their parent reference and thread structure stays intact.
    """
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    reply = await service.get_reply(reply_id, session)
    if not reply or reply.is_deleted:
        raise HTTPException(status_code=404, detail="Reply not found")
 
    user_id = UUID(token_details["user"]['user_id'])
    is_author = reply.author_id == user_id
    is_admin = await admin_service.verify_admin(token_details, session)
 
    if not is_author and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
 
    await service.delete_reply(reply, session)


# REPLY VOTES

@router.post("/replies/{reply_id}/vote", response_model=VoteResult)
async def vote_reply(
    reply_id: UUID,
    payload: VotePayload,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    """Same toggle/flip logic as thread votes."""
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    reply = await service.get_reply(reply_id, session)
    if not reply or reply.is_deleted:
        raise HTTPException(status_code=404, detail="Reply not found")
 
    user_id = UUID(token_details["user"]['user_id'])
    return await service.vote_reply(reply, user_id, payload, session)


@router.get("/replies/{reply_id}/vote", response_model=Optional[bool])
async def get_my_reply_vote(
    reply_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    user_id = UUID(token_details["user"]['user_id'])
    return await service.get_user_reply_vote(reply_id, user_id, session)


# REPLY ATTACHMENTS

@router.get("/replies/{reply_id}/attachments", response_model=list[ReplyAttachmentRead])
async def list_attachments(reply_id: UUID, session: SessionDependency):
    return await service.get_attachments(reply_id, session)


@router.post(
    "/replies/{reply_id}/attachments",
    response_model=ReplyAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_attachment(
    reply_id: UUID,
    payload: ReplyAttachmentCreate,     # { attachment_type, url, label? }
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    reply = await service.get_reply(reply_id, session)
    if not reply or reply.is_deleted:
        raise HTTPException(status_code=404, detail="Reply not found")
 
    user_id = UUID(token_details["user"]['user_id'])
    if reply.author_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
 
    return await service.add_attachment(reply_id, payload, session)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: UUID,
    session: SessionDependency,
    token_details: dict = access_token_bearer,
):
    if not await auth_service.is_valid_user_token(token_details, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid permissions")
 
    attachment = await service.get_attachment(attachment_id, session)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
 
    reply = await service.get_reply(attachment.reply_id, session)
    user_id = UUID(token_details["user"]['user_id'])
    is_author = reply and reply.author_id == user_id
    is_admin = await admin_service.verify_admin(token_details, session)
 
    if not is_author and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
 
    await service.delete_attachment(attachment, session)


# SEARCH  (frontend: search bar)

@router.get("/search", response_model=SearchResults)
async def search_forum(
    session: SessionDependency,
    query: str = Query(..., min_length=2),
    topic_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """
    Full-text search across thread titles/bodies and reply bodies.
    Optionally scoped to a single topic.
    Uses PostgreSQL ILIKE for simplicity; swap for tsvector if needed.
    """
    return await service.search_threads(q, topic_id, page, page_size, session)


# USER ACTIVITY  (frontend: profile pages)

@router.get("/users/{user_id}/threads", response_model=list[ThreadRead])
async def get_user_threads(
    user_id: UUID,
    session: SessionDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """All non-deleted threads by a user. Useful for profile pages."""
    return await service.get_user_threads(user_id, page, page_size, session)


@router.get("/users/{user_id}/replies", response_model=list[ReplyRead])
async def get_user_replies(
    user_id: UUID,
    session: SessionDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """All non-deleted replies by a user."""
    return await service.get_user_replies(user_id, page, page_size, session)