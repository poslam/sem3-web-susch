from database.database import get_session
from database.models import Airports, Countries
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import login_required

country_router = APIRouter()


@country_router.get("/view")
async def country_view(user=Depends(login_required),
                       session: AsyncSession = Depends(get_session)):

    countries = [x[0] for x in (await session.execute(select(Countries))).all()]

    return countries
