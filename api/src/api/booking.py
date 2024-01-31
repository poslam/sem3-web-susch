from random import randint
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
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from src.api.auth import login_required
from src.utils import exception

booking_router = APIRouter()


@booking_router.get("/view")
async def booking_view(
    user=Depends(login_required),
    session: AsyncSession = Depends(get_session),
):
    departure = aliased(Airports, name="arrival")
    arrival = aliased(Airports, name="departure")

    stmt = (
        select(
            Tickets.ID,
            Tickets.BookingReference,
            Tickets.Firstname,
            Tickets.Lastname,
            CabinTypes.Name.label("CabinTypeName"),
            Tickets.Phone,
            Schedules.FlightNumber,
            Schedules.Date,
            Schedules.Time,
            departure.IATACode.label("Departue"),
            arrival.IATACode.label("Arrival"),
            Routes.FlightTime,
            Aircrafts.Name.label("Aircraft"),
        )
        .where(Tickets.UserID == user.ID)
        .where(Tickets.CabinTypeID == CabinTypes.ID)
        .where(Tickets.ScheduleID == Schedules.ID)
        .where(Schedules.AircraftID == Aircrafts.ID)
        .where(Schedules.RouteID == Routes.ID)
        .where(Routes.DepartureAirportID == departure.ID)
        .where(Routes.ArrivalAirportID == arrival.ID)
        .order_by(Tickets.BookingReference)
    )

    result = []

    bookings = []

    tickets_raw = (await session.execute(stmt)).all()

    for ticket_raw in tickets_raw:
        ticket = ticket_raw._mapping

        if ticket["BookingReference"] not in bookings:
            bookings.append(ticket["BookingReference"])

            temp = dict(ticket)

            for x in ["Firstname", "Lastname", "CabinTypeName", "Phone"]:
                temp.pop(x)

            temp["Passengers"] = [
                {
                    x: ticket[x]
                    for x in ["Firstname", "Lastname", "CabinTypeName", "Phone"]
                }
            ]

            result.append(temp)

        else:
            result[-1]["Passengers"].append(
                {
                    x: ticket[x]
                    for x in ["Firstname", "Lastname", "CabinTypeName", "Phone"]
                }
            )

    return result


@booking_router.get("/check")
async def booking_check(
    schedule_ids: Union[str, int],  # 1,2,3
    number: int,
    cabin_type: Literal["eco", "bus", "fir"],
    user=Depends(login_required),
    session: AsyncSession = Depends(get_session),
):
    if isinstance(schedule_ids, int):
        schedules = [await session.get(Schedules, schedule_ids)]

    elif isinstance(schedule_ids, str):
        schedules: list[Schedules] = [
            x[0]
            for x in (
                await session.execute(
                    select(Schedules).where(
                        Schedules.ID.in_([int(y) for y in schedule_ids.split(",")])
                    )
                )
            ).all()
        ]

    result = []
    tickets_numbers = []
    numbers = [0, 0, 0]

    if schedules == []:
        await exception("schedules not found", 400, user.ID, session)

    for schedule in schedules:
        tickets_numbers.append(
            (
                await session.execute(
                    select(func.count(Tickets.ID))
                    .where(Tickets.ScheduleID == schedule.ID)
                    .where(Tickets.CabinTypeID == 1)
                )
            )
            .first()
            ._mapping["count"]
        )

        tickets_numbers.append(
            (
                await session.execute(
                    select(func.count(Tickets.ID))
                    .where(Tickets.ScheduleID == schedule.ID)
                    .where(Tickets.CabinTypeID == 2)
                )
            )
            .first()
            ._mapping["count"]
        )

        tickets_numbers.append(
            (
                await session.execute(
                    select(func.count(Tickets.ID))
                    .where(Tickets.ScheduleID == schedule.ID)
                    .where(Tickets.CabinTypeID == 3)
                )
            )
            .first()
            ._mapping["count"]
        )

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
                "FreeEconomySeats": aircraft.EconomySeats
                - tickets_numbers[0]
                - numbers[0],
                "FreeBusinessSeats": aircraft.BusinessSeats
                - tickets_numbers[1]
                - numbers[1],
                "FreeFirstClassSeats": (
                    aircraft.TotalSeats - aircraft.BusinessSeats - aircraft.EconomySeats
                )
                - tickets_numbers[2]
                - numbers[2],
            }
        )

    return result


@booking_router.post("/add")
async def booking_add(
    request: Request,
    cabin_type: Literal["eco", "bus", "fir"],
    schedule_ids: Union[str, int],  # 1,2,3
    user=Depends(login_required),
    session: AsyncSession = Depends(get_session),
):
    passengers = await request.json()

    if isinstance(schedule_ids, int):
        schedules = [await session.get(Schedules, schedule_ids)]

    elif isinstance(schedule_ids, str):
        schedules: list[Schedules] = [
            x[0]
            for x in (
                await session.execute(
                    select(Schedules).where(
                        Schedules.ID.in_([int(y) for y in schedule_ids.split(",")])
                    )
                )
            ).all()
        ]

    if schedules == []:
        await exception("schedules not found", 400, user.ID, session)

    if cabin_type == "eco":
        cabin_type_id = 1
    elif cabin_type == "bus":
        cabin_type_id = 2
    else:
        cabin_type_id = 3

    codes = [
        x._mapping["distinct"]
        for x in (
            await session.execute(select(func.distinct(Tickets.BookingReference)))
        ).all()
    ]

    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    code = "".join([alphabet[randint(0, 25)] for _ in range(6)])

    while code in codes:
        code = "".join([alphabet[randint(0, 25)] for _ in range(6)])

    for passenger in passengers:
        country = (
            await session.execute(
                select(Countries).where(Countries.Name == passenger["Country Name"])
            )
        ).first()

        if country == None:
            await exception("country not found", 400, user.ID, session)

        country: Countries = country[0]

        for schedule in schedules:
            ticket = {
                "UserID": user.ID,
                "ScheduleID": schedule.ID,
                "CabinTypeID": cabin_type_id,
                "Firstname": passenger["Firstname"],
                "Lastname": passenger["Lastname"],
                "Phone": passenger["Phone"],
                "PassportNumber": passenger["Passport number"],
                "PassportCountryID": country.ID,
                "BookingReference": code,
                "Confirmed": 0,
            }

            await session.execute(insert(Tickets).values(ticket))

    await session.commit()

    return {"detail": "booking add success", "code": code}


@booking_router.post("/confirm")
async def booking_confirm(
    code: str,
    user=Depends(login_required),
    session: AsyncSession = Depends(get_session),
):
    bookings = [
        x[0]
        for x in (
            await session.execute(
                select(Tickets).where(Tickets.BookingReference == code)
            )
        ).all()
    ]

    if bookings == []:
        await exception("booking not found", 400, user.ID, session)

    await session.execute(
        update(Tickets).where(Tickets.BookingReference == code).values(Confirmed=1)
    )
    await session.commit()

    return {"detail": "booking confirm success"}
