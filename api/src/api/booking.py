from typing import Literal, Union

from database.database import get_session
from database.models import (
    Aircrafts,
    Airports,
    CabinTypes,
    Countries,
    Routes,
    Schedules,
    Tickets,
)
from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import desc, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from src.api.auth import login_required
from src.utils import exception

booking_router = APIRouter()


@booking_router.get("/check")
async def booking_check(schedule_ids: Union[str, int],  # 1,2,3
                        number: int,
                        cabin_type: Literal["eco", "bus", "fir"],
                        user=Depends(login_required),
                        session: AsyncSession = Depends(get_session)):

    if isinstance(schedule_ids, int):
        schedules = [await session.get(Schedules, schedule_ids)]

    elif isinstance(schedule_ids, str):
        schedules: list[Schedules] = [x[0] for x in (await session.execute(
            select(Schedules).where(Schedules.ID.in_(
                [int(y) for y in schedule_ids.split(',')]))
        )).all()]

    result = []
    tickets_numbers = []
    numbers = [0, 0, 0]

    if schedules == []:
        await exception("schedules not found", 400, user.ID, session)

    for schedule in schedules:

        tickets_numbers.append((await session.execute(
            select(func.count(Tickets.ID))
            .where(Tickets.ScheduleID == schedule.ID)
            .where(Tickets.CabinTypeID == 1)
        )).first()._mapping["count"])

        tickets_numbers.append((await session.execute(
            select(func.count(Tickets.ID))
            .where(Tickets.ScheduleID == schedule.ID)
            .where(Tickets.CabinTypeID == 2)
        )).first()._mapping["count"])

        tickets_numbers.append((await session.execute(
            select(func.count(Tickets.ID))
            .where(Tickets.ScheduleID == schedule.ID)
            .where(Tickets.CabinTypeID == 3)
        )).first()._mapping["count"])

        if cabin_type == "eco":
            numbers[0] = number
        elif cabin_type == "bus":
            numbers[1] = number
        else:
            numbers[2] = number

        aircraft = await session.get(Aircrafts, schedule.AircraftID)

        result.append(
            {
                "ScheduleID": schedule.ID,
                "FreeEconomySeats": aircraft.EconomySeats-tickets_numbers[0]-numbers[0],
                "FreeBusinessSeats": aircraft.BusinessSeats-tickets_numbers[1]-numbers[1],
                "FreeFirstClassSeats": (aircraft.TotalSeats - aircraft.BusinessSeats -
                                        aircraft.EconomySeats)-tickets_numbers[2]-numbers[2]
            }
        )

    return result


@booking_router.post("/add")
async def booking_add(request: Request,
                      cabin_type: Literal["eco", "bus", "fir"],
                      user=Depends(login_required),
                      session: AsyncSession = Depends(get_session)):

    data = await request.json()
    passangers = []

    try:

        for passanger in data:
            
            passangers.append()

    except:
        await exception("incorrect request", 400, user.ID, session)
