"""Database operations with users."""
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def add_user(session: AsyncSession, uid: str, spotify_id: str):
    """Add new user if not exists."""
    user = (await session.execute(sa.select(User).where(User.spotify_id == spotify_id))).scalar()

    if user is not None:
        if user.uid != uid:
            user.uid = uid
    else:
        (
            await session.execute(sa.insert(User).values(uid=uid, spotify_id=spotify_id).returning(User.uid))
        )

    await session.commit()
