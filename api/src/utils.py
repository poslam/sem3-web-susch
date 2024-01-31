from datetime import datetime, timedelta

from database.database import get_session
from database.models import Logs
from fastapi import Depends, HTTPException
from sqlalchemy import desc, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


def time():
    return datetime.utcnow() + timedelta(hours=10)


async def exception(
    detail: str,
    status_code: int,
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        last_id = (
            (await session.execute(select(Logs.ID).order_by(desc(Logs.ID))))
            .all()[0]
            ._mapping["ID"]
        )
    except:
        last_id = 0

    log_insert = {"ID": last_id + 1, "Time": time(), "Error": detail, "UserID": user_id}

    await session.execute(insert(Logs).values(log_insert))
    await session.commit()

    raise HTTPException(status_code=status_code, detail=detail)
