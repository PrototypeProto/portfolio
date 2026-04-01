from sqlmodel import SQLModel, Field, Column
from typing import Optional
from db.db_models import MemberRoleEnum
from datetime import date, datetime, time


class UserRead(SQLModel):
    user_id: UUID
    username: str
    nickname: Optional[str]
    join_date: date
    role: MemberRoleEnum


class UserPrivateRead(UserRead):
    email: Optional[str]
    last_login_date: Optional[date]


class PendingUserRead(SQLModel):
    user_id: UUID
    username: str
    email: Optional[str]
    nickname: Optional[str]
    join_date: date
    request: Optional[str]


# # # # # # # # # #
# Topics
# # # # # # # # # #
class TopicGroupRead(SQLModel):
    group_id: UUID
    name: str
    display_order: int


class TopicRead(SQLModel):
    topic_id: UUID
    group_id: Optional[UUID]

    name: str
    description: Optional[str]
    icon_url: Optional[str]

    display_order: int

    thread_count: int
    reply_count: int

    is_locked: bool

    last_activity_at: Optional[datetime]
    last_thread_id: Optional[UUID]


class TopicWithGroupRead(TopicRead):
    group: Optional[TopicGroupRead]


# TOPIC WRITE MODELS
class TopicCreate(SQLModel):
    group_id: Optional[UUID] = None
    name: str = Field(max_length=100)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    display_order: int = 0


class TopicUpdate(SQLModel):
    group_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    display_order: Optional[int] = None
    is_locked: Optional[bool] = (
        None  # prefer the dedicated /lock endpoint, but available here for bulk admin updates
    )


class TopicGroupCreate(SQLModel):
    name: str = Field(max_length=100)
    display_order: int = 0


class TopicGroupUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    display_order: Optional[int] = None


# # # # # # # # # #
# Threads
# # # # # # # # # #
class ThreadRead(SQLModel):
    thread_id: UUID
    topic_id: UUID

    author_id: UUID
    author_username: str  # to display poster name

    title: str
    body: str

    created_at: datetime
    updated_at: Optional[datetime]

    is_pinned: bool
    is_locked: bool

    reply_count: int
    upvote_count: int
    downvote_count: int


class ThreadListItem(SQLModel):
    thread_id: UUID
    title: str
    author_id: UUID
    created_at: datetime

    reply_count: int
    upvote_count: int
    downvote_count: int

    is_pinned: bool


class ThreadWithVote(ThreadRead):
    user_vote: Optional[bool]  # True = upvote, False = downvote, None = no vote


# THREAD WRITE MODELS
class ThreadCreate(SQLModel):
    title: str = Field(max_length=200)
    body: str

class ThreadUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=200)
    body: Optional[str] = None
    # mod-only fields — enforce in the endpoint, not the model
    is_pinned: Optional[bool] = None
    pin_expires_at: Optional[datetime] = None
    is_locked: Optional[bool] = None

class PaginatedThreads(SQLModel):
    items: list[ThreadListItem]
    total: int
    page: int
    page_size: int
    pages: int




# SEARCH
class SearchResults(SQLModel):
    query: str
    threads: list[ThreadListItem]
    total: int


# # # # # # # # # #
# Replies
# # # # # # # # # #
class ReplyRead(SQLModel):
    reply_id: UUID
    thread_id: UUID
    author_id: UUID
    author_username: Optional[str] # JOIN
    parent_reply_id: Optional[UUID]

    body: str

    created_at: datetime
    updated_at: Optional[datetime]

    upvote_count: int
    downvote_count: int


class ReplyTree(ReplyRead):
    children: list["ReplyTree"] = []


class ReplyWithVote(ReplyRead):
    user_vote: Optional[bool]  # True = upvote, False = downvote, None = no vote


class ReplyAttachmentRead(SQLModel):
    attachment_id: UUID
    reply_id: UUID

    attachment_type: AttachmentType
    url: str
    label: Optional[str]

    created_at: datetime

class PaginatedReplies(SQLModel):
    items: list[ReplyRead]
    total: int
    page: int
    page_size: int
    pages: int

# REPLY WRITE MODELS
class ReplyCreate(SQLModel):
    body: str
    parent_reply_id: Optional[UUID] = None


class ReplyUpdate(SQLModel):
    body: str  # only the body is ever editable by the author


# ATTACHMENT WRITE MODELS
class ReplyAttachmentCreate(SQLModel):
    attachment_type: AttachmentType
    url: str = Field(max_length=2048)
    label: Optional[str] = Field(default=None, max_length=200)


# # # # # # # # # #
# VOTE PAYLOADS / RESULTS
# # # # # # # # # #
class VotePayload(SQLModel):
    is_upvote: bool


class VoteResult(SQLModel):
    upvote_count: int
    downvote_count: int


# class ThreadRead(SQLModel):
#     thread_id: UUID
#     topic_id: UUID
#     author_id: UUID

#     title: str
#     body: str

#     created_at: datetime
#     updated_at: Optional[datetime]

#     is_pinned: bool
#     pin_expires_at: Optional[datetime]
#     is_locked: bool

#     reply_count: int
#     upvote_count: int
#     downvote_count: int
#     view_count: int


# NOTE: use this when doing joins
# def thread_to_read(thread: Thread, username: str) -> ThreadRead:
#     return ThreadRead(**thread.dict(), author_username=username)

# threads = [
#     ThreadRead(
#         **thread.dict(),
#         author_username=username
#     )
#     for thread, username in results
# ]
