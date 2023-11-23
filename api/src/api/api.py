from database.database import get_session
from database.models import User
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import auth_router

api_router = APIRouter(
    prefix="/api"
)

api_router.include_router(auth_router)


@api_router.get("/serverStatus")
async def test(back: BackgroundTasks,
               session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(select(User))
        return {"detail": "server and database are working!"}
    except Exception as e:
        print(e)
        return {"detail": "connection to the database is corrupted"}
