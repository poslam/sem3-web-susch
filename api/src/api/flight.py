from datetime import date, time

from database.database import get_session
from database.models import Aircrafts, Airports, Routes, Schedules
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import desc, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from src.api.auth import admin_required
from src.utils import exception

flight_router = APIRouter()


@flight_router.get("/search")
async def flight_search(departure_airport: str = None,
                        arrival_airport: str = None,
                        departure_date: date = None,
                        flight_number: str = None,
                        begin: time = None,
                        end: time = None,
                        user=Depends(admin_required),
                        session: AsyncSession = Depends(get_session)):

    departure = aliased(Airports, name='arrival')
    arrival = aliased(Airports, name='departure')

    stmt = (select(Schedules.Date,
                   Schedules.Time,
                   departure.IATACode.label('FROM'),
                   arrival.IATACode.label('TO'),
                   Schedules.FlightNumber,
                   Aircrafts.Name.label('Aircraft'),
                   Schedules.EconomyPrice,
                   func.floor(Schedules.EconomyPrice *
                              1.3).label('BuisnessPrice'),
                   func.floor((Schedules.EconomyPrice * 1.3)
                              * 1.35).label('FirstClassPrice'),
                   Schedules.Confirmed
                   ).where(Schedules.AircraftID == Aircrafts.ID)
            .where(Schedules.RouteID == Routes.ID)
            .where(Routes.DepartureAirportID == departure.ID)
            .where(Routes.ArrivalAirportID == arrival.ID)
            )

    if departure_airport != None:
        stmt = (stmt
                .where(departure.IATACode == departure_airport))

    if arrival_airport != None:
        stmt = (stmt
                .where(arrival.IATACode == arrival_airport))

    if departure_date != None:
        stmt = (stmt
                .where(Schedules.Date == departure_date))

    if flight_number != None:
        stmt = (stmt
                .where(Schedules.FlightNumber == flight_number))

    if begin != None:
        stmt = (stmt
                .where(Schedules.Time >= begin))

    if end != None:
        stmt = (stmt
                .where(Schedules.Time <= end))

    scheduless_raw = (await session.execute(stmt)).all()
    sessions = []

    for schedules_raw in scheduless_raw:
        if schedules_raw:
            sessions.append(schedules_raw._mapping)

    if sessions:
        return sessions
    else:
        return {"detail": "no flight schedules found"}


@flight_router.post("/confirm")
async def flight_confirm(schedules_id: int,
                         user=Depends(admin_required),
                         session: AsyncSession = Depends(get_session)):

    schedules_for_confirm: Schedules = await session.get(Schedules, schedules_id)

    if schedules_for_confirm == None:
        await exception("schedule not found", 400, user.ID, session)

    if (schedules_for_confirm.Confirmed == 0):
        await session.execute(
            update(Schedules)
            .where(Schedules.ID == schedules_id)
            .values(Confirmed=1)
        )
        await session.commit()
        response = {"detail": "schedule confirmed"}
    else:
        await session.execute(
            update(Schedules)
            .where(Schedules.ID == schedules_id)
            .values(Confirmed=0)
        )
        await session.commit()
        response = {"detail": "schedule unconfirmed"}

    return response


@flight_router.put("/edit")
async def flight_edit(flight_id: int,
                      new_date: date = None,
                      new_time: time = None,
                      new_economy_price: int = None,
                      user=Depends(admin_required),
                      session: AsyncSession = Depends(get_session)):

    flight_to_edit: Schedules = await session.get(Schedules, flight_id)

    if flight_to_edit is None:
        await exception("flight schedule not found", 400, user.ID, session)

    if new_date:
        flight_to_edit.Date = new_date
    if new_time:
        flight_to_edit.Time = new_time
    if new_economy_price:
        flight_to_edit.EconomyPrice = new_economy_price

    await session.commit()

    return {"detail": "flight schedule updated successfully"}


@flight_router.post("/import")
async def flight_import(file: UploadFile = File(...),
                        user=Depends(admin_required),
                        session: AsyncSession = Depends(get_session)):

    lines = (await file.read()).decode('utf-8').split('\n')
    stmts = []

    dubles = 0
    not_allowed = 0

    for line in lines:

        data = line.split(',')

        if "OK" in data[8]:
            data[8] = 1
        else:
            data[8] = 0

        if data[0] == 'EDIT':

            schedule_raw = (await session.execute(
                select(Schedules)
                .where(Schedules.Date == data[1])
                .where(Schedules.FlightNumber == data[3])
            )).first()

            if schedule_raw == None:
                not_allowed += 1
                continue

            schedule: Schedules = schedule_raw[0]

            aircraft = await session.get(Aircrafts, data[6])

            departure_airport_raw = (await session.execute(
                select(Airports)
                .where(Airports.IATACode == data[4])
            )).first()

            arrival_airport_raw = (await session.execute(
                select(Airports)
                .where(Airports.IATACode == data[5])
            )).first()

            if any(x == None for x in [aircraft, departure_airport_raw, arrival_airport_raw]):
                not_allowed += 1
                continue

            departure_airport: Airports = departure_airport_raw[0]
            arrival_airport: Airports = arrival_airport_raw[0]

            route_raw = (await session.execute(
                select(Routes)
                .where(Routes.DepartureAirportID == departure_airport.ID)
                .where(Routes.ArrivalAirportID == arrival_airport.ID)
            )).first()

            if route_raw == None:
                not_allowed += 1
                continue

            route: Routes = route_raw[0]

            schedule_ins = {"Date": data[1],
                            "Time": data[2],
                            "AircraftID": aircraft.ID,
                            "RouteID": route.ID,
                            "FlightNumber": data[3],
                            "EconomyPrice": float(data[7]),
                            "Confirmed": data[8]}

            stmts.append(update(Schedules)
                         .where(Schedules.ID == schedule.ID)
                         .values(schedule_ins))

        elif data[0] == 'ADD':

            schedule_duble = (await session.execute(
                select(Schedules)
                .where(Schedules.Date == data[1])
                .where(Schedules.FlightNumber == data[3])
            )).first()

            if schedule_duble != None:
                dubles += 1
                continue

            aircraft = await session.get(Aircrafts, data[6])

            departure_airport_raw = (await session.execute(
                select(Airports)
                .where(Airports.IATACode == data[4])
            )).first()

            arrival_airport_raw = (await session.execute(
                select(Airports)
                .where(Airports.IATACode == data[5])
            )).first()

            if any(x == None for x in [aircraft, departure_airport_raw, arrival_airport_raw]):
                not_allowed += 1
                continue

            departure_airport: Airports = departure_airport_raw[0]
            arrival_airport: Airports = arrival_airport_raw[0]

            route_raw = (await session.execute(
                select(Routes)
                .where(Routes.DepartureAirportID == departure_airport.ID)
                .where(Routes.ArrivalAirportID == arrival_airport.ID)
            )).first()

            if route_raw == None:
                not_allowed += 1
                continue

            route: Routes = route_raw[0]

            schedule_ins = {"Date": data[1],
                            "Time": data[2],
                            "AircraftID": aircraft.ID,
                            "RouteID": route.ID,
                            "FlightNumber": data[3],
                            "EconomyPrice": float(data[7]),
                            "Confirmed": data[8]}

            stmts.append(insert(Schedules).values(schedule_ins))

        else:
            not_allowed += 1

    if not_allowed > 0:
        raise exception(
            f"incorrect import file. number of wrong rows: {not_allowed}")

    for stmt in stmts:
        await session.execute(stmt)

    await session.commit()

    return {"detail": "flight import success", "duplicates": dubles}
