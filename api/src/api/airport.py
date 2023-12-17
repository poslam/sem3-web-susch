from database.database import get_session
from database.models import Airports, Countries
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import login_required

airport_router = APIRouter()


@airport_router.get("/view")
async def airport_view(user=Depends(login_required),
                       session: AsyncSession = Depends(get_session)):

    airports = [x._mapping for x in (await session.execute(
        select(Airports.ID,
               Airports.IATACode,
               Airports.Name,
               Countries.Name.label("CountryName"))
        .where(Airports.CountryID == Countries.ID)
    )).all()]

    return airports
