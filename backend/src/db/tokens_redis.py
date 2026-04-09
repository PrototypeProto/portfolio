import redis.asyncio as redis
from src.config import Config
from datetime import datetime, timezone

# db=0: JTI blocklist (revoked access + refresh tokens)
redis_token_blocklist = redis.Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    password=Config.REDIS_PASSWORD,
    db=0,
)

# db=1: Active refresh token family store
# Key:   refresh_jti  →  username
# Used to validate that an incoming refresh token was actually issued by us
# and hasn't already been rotated (reuse = family revocation).
redis_refresh_store = redis.Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    password=Config.REDIS_PASSWORD,
    db=1,
)


# ---------------------------------------------------------------------------
# JTI blocklist
# ---------------------------------------------------------------------------


async def add_jti_to_blocklist(jti: str, ttl_seconds: int) -> None:
    """
    Blocklist a JTI for exactly as long as the token would have been valid.
    Once the TTL expires Redis removes the key automatically, keeping the
    blocklist lean.
    """
    await redis_token_blocklist.set(name=jti, value="", ex=ttl_seconds)


async def token_in_blocklist(jti: str) -> bool:
    return await redis_token_blocklist.get(jti) is not None


# ---------------------------------------------------------------------------
# Refresh token family store
# ---------------------------------------------------------------------------


async def store_refresh_token(jti: str, username: str, ttl_seconds: int) -> None:
    """Record a newly issued refresh token JTI."""
    await redis_refresh_store.set(name=jti, value=username, ex=ttl_seconds)


async def get_refresh_token_owner(jti: str) -> str | None:
    """Return the username that owns this refresh JTI, or None if unknown/expired."""
    value = await redis_refresh_store.get(jti)
    return value.decode() if value is not None else None


async def delete_refresh_token(jti: str) -> None:
    """Remove a refresh JTI from the store (called on rotation)."""
    await redis_refresh_store.delete(jti)


async def revoke_all_user_refresh_tokens(username: str) -> None:
    """
    Scan the refresh store for every JTI belonging to `username` and delete
    them all.  Called when reuse of an already-rotated token is detected
    (family revocation) or on explicit logout.

    Note: SCAN is O(N) over the refresh store keyspace.  This store only
    ever holds live refresh tokens (TTL-bounded) so it stays small.
    """
    cursor = 0
    to_delete: list[str] = []

    while True:
        cursor, keys = await redis_refresh_store.scan(cursor=cursor, count=100)
        for key in keys:
            owner = await redis_refresh_store.get(key)
            if owner and owner.decode() == username:
                to_delete.append(key)
        if cursor == 0:
            break

    if to_delete:
        await redis_refresh_store.delete(*to_delete)
