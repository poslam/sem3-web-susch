from datetime import datetime

from database.database import get_session
from database.models import Offices, Users
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import admin_required
from src.utils import time

office_router = APIRouter()


@office_router.get("/view")
async def office_view(user=Depends(admin_required),
                      session: AsyncSession = Depends(get_session)):

    return [x[0] for x in (await session.execute(select(Offices))).all()]
