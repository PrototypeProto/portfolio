import redis.asyncio as redis
from src.config import Config
from datetime import timedelta
from src.db.db_models import MemberRoleEnum

USER_EXPIRY = None


redis_user = redis.Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=2
)


async def add_registered_user(username: str, role: MemberRoleEnum) -> None:
    await redis_user.set(
        name=username,
        value=role.value,
        ex=USER_EXPIRY
    )

async def get_user(username: str) -> MemberRoleEnum | None:
    role = await redis_user.get(username)
    if role is None:
        return None

    try:
        return MemberRoleEnum(role.decode())
    except:
        raise Exception("Failed to decode role")

async def remove_user(username: str) -> None:
    await redis_user.delete(username)
    
