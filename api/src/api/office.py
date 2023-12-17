from datetime import datetime

from database.database import get_session
from database.models import Countries, Offices, Users
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import admin_required
from src.utils import time

office_router = APIRouter()


@office_router.get("/view")
async def office_view(user=Depends(admin_required),
                      session: AsyncSession = Depends(get_session)):

    offices = [x._mapping for x in (await session.execute(
        select(Offices.ID,
               Offices.Title,
               Offices.Phone,
               Offices.Contact,
               Countries.Name.label("CountryName"))
        .where(Offices.CountryID == Countries.ID)
    )).all()]

    return offices
