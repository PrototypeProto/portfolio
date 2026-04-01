from math import ceil
from src.db.models import *
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc, update, insert, delete, func
from datetime import date, datetime, timedelta
from uuid import UUID
from typing import Tuple
from src.db.db_models import MemberRoleEnum, VerifyUserModel
from src.db.read_models import *
from src.db.roles_redis import set_user_role, get_user_role
from src.db.users_redis import add_registered_user, get_user, remove_user
from src.auth.service import AuthService

auth_service = AuthService()


class ForumService:
    """
    Handles business logic for the {/forum} route
    Only USERS+ may use this
    May be sectioned to allow subsections of users for certain topics
    """

    # # # # # # # # # # # # # # # # # # # # # # # #
    #   TOPIC Methods
    # # # # # # # # # # # # # # # # # # # # # # # #

    async def get_topic_groups(self, session: AsyncSession) -> list[TopicGroup]:
        result = await session.exec(select(TopicGroup).order_by(TopicGroup.display_order))
        return result.all()

    async def retrieve_topics(
        self, group_id: Optional[UUID], session: AsyncSession
    ) -> list[Topic]:
        query = select(Topic).order_by(Topic.display_order)
        if group_id:
            query = query.where(Topic.group_id == group_id)
        result = await session.exec(query)
        return result.all()

    async def get_topic(self, topic_id: UUID, session: AsyncSession) -> TopicRead:
        return await session.get(Topic, topic_id)

    # NOTE: ADMIN ONLY
    async def create_topic(self, payload: TopicCreate, session: AsyncSession) -> Topic:
        topic = Topic(**payload.model_dump())
        session.add(topic)
        await session.commit()
        await session.refresh(topic)
        return topic

    async def update_topic(
        self, topic_id: UUID, payload: TopicUpdate, session: AsyncSession
    ) -> Topic:
        topic = await session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(topic, field, value)
        await session.commit()
        await session.refresh(topic)
        return topic

    async def toggle_topic_lock(self, topic_id: UUID, session: AsyncSession) -> Topic:
        topic = await session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        topic.is_locked = not topic.is_locked
        await session.commit()
        await session.refresh(topic)
        return topic

    # extra

    async def get_threads(
        self,
        topic_id: UUID,
        page: int,
        page_size: int,
        sort: str,
        session: AsyncSession,
    ) -> PaginatedThreads:
        base_query = (
            select(Thread)
            .where(Thread.topic_id == topic_id)
            .where(Thread.is_deleted == False)
        )

        # pinned threads always first, then apply sort within each group
        if sort == "top":
            order = [Thread.is_pinned.desc(), Thread.upvote_count.desc()]
        elif sort == "oldest":
            order = [Thread.is_pinned.desc(), Thread.created_at.asc()]
        else:  # latest
            order = [Thread.is_pinned.desc(), Thread.created_at.desc()]

        total = await session.exec(
            select(func.count()).select_from(base_query.subquery())
        ).one()

        threads = await session.exec(
            base_query.order_by(*order).offset((page - 1) * page_size).limit(page_size)
        ).all()

        return ThreadListResponse(
            threads=threads,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size),
        )

    async def get_thread(self, thread_id: UUID, session: AsyncSession) -> Optional[ThreadRead]:
        return await session.get(Thread, thread_id)

    async def create_thread(
        self, topic_id: UUID, author_id: UUID, payload: ThreadCreate, session: AsyncSession
    ):
        thread = Thread(
            topic_id=topic_id,
            author_id=author_id,
            **payload.model_dump(),
        )
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
        return thread

    async def update_thread(self, thread: Thread, payload: ThreadUpdate, session: AsyncSession) -> Thread:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(thread, field, value)

        thread.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(thread)
        return thread

    async def delete_thread(self, thread: Thread, session: AsyncSession) -> None:
        thread.is_deleted = True
        await session.commit()
 
    async def toggle_thread_lock(self, thread: Thread, session: AsyncSession) -> Thread:
        thread.is_locked = not thread.is_locked
        await session.commit()
        await session.refresh(thread)
        return thread
 
    async def toggle_thread_pin(
        self, thread: Thread, pin_expires_at: Optional[datetime], session: AsyncSession
    ) -> Thread:
        thread.is_pinned = not thread.is_pinned
        thread.pin_expires_at = pin_expires_at if thread.is_pinned else None
        await session.commit()
        await session.refresh(thread)
        return thread
 
    #  THREAD VOTES
 
    async def vote_thread(
        self, thread: Thread, user_id: UUID, payload: VotePayload, session: AsyncSession
    ) -> VoteResult:
        existing = (await session.exec(
            select(ThreadVote)
            .where(ThreadVote.user_id == user_id)
            .where(ThreadVote.thread_id == thread.thread_id)
        )).first()
 
        if existing:
            if existing.is_upvote == payload.is_upvote:
                # same vote → un-vote
                if existing.is_upvote:
                    thread.upvote_count = max(0, thread.upvote_count - 1)
                else:
                    thread.downvote_count = max(0, thread.downvote_count - 1)
                await session.delete(existing)
            else:
                # flip vote
                if payload.is_upvote:
                    thread.upvote_count += 1
                    thread.downvote_count = max(0, thread.downvote_count - 1)
                else:
                    thread.downvote_count += 1
                    thread.upvote_count = max(0, thread.upvote_count - 1)
                existing.is_upvote = payload.is_upvote
        else:
            session.add(ThreadVote(user_id=user_id, thread_id=thread.thread_id, is_upvote=payload.is_upvote))
            if payload.is_upvote:
                thread.upvote_count += 1
            else:
                thread.downvote_count += 1
 
        await session.commit()
        await session.refresh(thread)
        return VoteResult(upvote_count=thread.upvote_count, downvote_count=thread.downvote_count)
 
    async def get_user_thread_vote(
        self, thread_id: UUID, user_id: UUID, session: AsyncSession
    ) -> Optional[VotePayload]:
        vote = (await session.exec(
            select(ThreadVote)
            .where(ThreadVote.user_id == user_id)
            .where(ThreadVote.thread_id == thread_id)
        )).first()
        return VotePayload(is_upvote=vote.is_upvote) if vote else None
 
    #  REPLIES
 
    async def get_replies(
        self, thread_id: UUID, page: int, page_size: int, session: AsyncSession
    ) -> PaginatedReplies:
        base_q = (
            select(Reply)
            .where(Reply.thread_id == thread_id)
            .where(Reply.parent_reply_id == None)
        )
        total = (await session.exec(select(func.count()).select_from(base_q.subquery()))).one()
        replies = (await session.exec(
            base_q.order_by(Reply.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()
 
        return PaginatedReplies(
            items=replies,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size),
        )
 
    async def get_reply_children(self, reply_id: UUID, session: AsyncSession) -> list[Reply]:
        result = await session.exec(
            select(Reply).where(Reply.parent_reply_id == reply_id).order_by(Reply.created_at.asc())
        )
        return result.all()
 
    async def get_reply(self, reply_id: UUID, session: AsyncSession) -> Optional[Reply]:
        return await session.get(Reply, reply_id)
 
    async def create_reply(
        self, thread_id: UUID, author_id: UUID, payload: ReplyCreate, session: AsyncSession
    ) -> Reply:
        reply = Reply(thread_id=thread_id, author_id=author_id, **payload.model_dump())
        session.add(reply)
        await session.commit()
        await session.refresh(reply)
        return reply
 
    async def update_reply(
        self, reply: Reply, payload: ReplyUpdate, session: AsyncSession
    ) -> Reply:
        reply.body = payload.body
        reply.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(reply)
        return reply
 
    async def delete_reply(self, reply: Reply, session: AsyncSession) -> None:
        reply.is_deleted = True
        await session.commit()
 
    #  REPLY VOTES
 
    async def vote_reply(
        self, reply: Reply, user_id: UUID, payload: VotePayload, session: AsyncSession
    ) -> VoteResult:
        existing = (await session.exec(
            select(ReplyVote)
            .where(ReplyVote.user_id == user_id)
            .where(ReplyVote.reply_id == reply.reply_id)
        )).first()
 
        if existing:
            if existing.is_upvote == payload.is_upvote:
                if existing.is_upvote:
                    reply.upvote_count = max(0, reply.upvote_count - 1)
                else:
                    reply.downvote_count = max(0, reply.downvote_count - 1)
                await session.delete(existing)
            else:
                if payload.is_upvote:
                    reply.upvote_count += 1
                    reply.downvote_count = max(0, reply.downvote_count - 1)
                else:
                    reply.downvote_count += 1
                    reply.upvote_count = max(0, reply.upvote_count - 1)
                existing.is_upvote = payload.is_upvote
        else:
            session.add(ReplyVote(user_id=user_id, reply_id=reply.reply_id, is_upvote=payload.is_upvote))
            if payload.is_upvote:
                reply.upvote_count += 1
            else:
                reply.downvote_count += 1
 
        await session.commit()
        await session.refresh(reply)
        return VoteResult(upvote_count=reply.upvote_count, downvote_count=reply.downvote_count)
 
    async def get_user_reply_vote(
        self, reply_id: UUID, user_id: UUID, session: AsyncSession
    ) -> Optional[bool]:
        vote = (await session.exec(
            select(ReplyVote)
            .where(ReplyVote.user_id == user_id)
            .where(ReplyVote.reply_id == reply_id)
        )).first()
        return vote.is_upvote if vote else None
 
    #  REPLY ATTACHMENTS
 
    async def get_attachments(self, reply_id: UUID, session: AsyncSession) -> list[ReplyAttachment]:
        result = await session.exec(
            select(ReplyAttachment).where(ReplyAttachment.reply_id == reply_id)
        )
        return result.all()
 
    async def get_attachment(self, attachment_id: UUID, session: AsyncSession) -> Optional[ReplyAttachment]:
        return await session.get(ReplyAttachment, attachment_id)
 
    async def add_attachment(
        self, reply_id: UUID, payload: ReplyAttachmentCreate, session: AsyncSession
    ) -> ReplyAttachment:
        attachment = ReplyAttachment(reply_id=reply_id, **payload.model_dump())
        session.add(attachment)
        await session.commit()
        await session.refresh(attachment)
        return attachment
 
    async def delete_attachment(self, attachment: ReplyAttachment, session: AsyncSession) -> None:
        await session.delete(attachment)
        await session.commit()
 
    #  SEARCH
 
    async def search_threads(
        self,
        q: str,
        topic_id: Optional[UUID],
        page: int,
        page_size: int,
        session: AsyncSession,
    ) -> SearchResults:
        term = f"%{q}%"
        query = (
            select(Thread)
            .where(Thread.is_deleted == False)
            .where(Thread.title.ilike(term) | Thread.body.ilike(term))
        )
        if topic_id:
            query = query.where(Thread.topic_id == topic_id)
 
        threads = (await session.exec(
            query.order_by(Thread.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()
 
        return SearchResults(query=q, threads=threads, total=len(threads))
 
    #  USER ACTIVITY
 
    async def get_user_threads(
        self, user_id: UUID, page: int, page_size: int, session: AsyncSession
    ) -> list[Thread]:
        result = await session.exec(
            select(Thread)
            .where(Thread.author_id == user_id)
            .where(Thread.is_deleted == False)
            .order_by(Thread.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.all()
 
    async def get_user_replies(
        self, user_id: UUID, page: int, page_size: int, session: AsyncSession
    ) -> list[Reply]:
        result = await session.exec(
            select(Reply)
            .where(Reply.author_id == user_id)
            .where(Reply.is_deleted == False)
            .order_by(Reply.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.all()





