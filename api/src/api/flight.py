import calendar
from datetime import date, datetime, time, timedelta

from config import EXCEL_PATH
from database.database import get_session
from database.models import Aircrafts, Airports, Routes, Schedules
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from pandas import DataFrame, ExcelWriter
from sqlalchemy import desc, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from src.api.auth import admin_required, login_required
from src.utils import exception

flight_router = APIRouter()

max_transfers = 2


@flight_router.get("/view")
async def flight_view(
    departure_airport_code: str,
    arrival_airport_code: str,
    date_to: date,
    date_from: date = None,
    mode: str = "to",  # to, to-from
    user=Depends(login_required),
    session: AsyncSession = Depends(get_session),
):
    result = {"to": [], "from": []}

    departure_airport_raw = (
        await session.execute(
            select(Airports).where(Airports.IATACode == departure_airport_code)
        )
    ).first()

    arrival_airport_raw = (
        await session.execute(
            select(Airports).where(Airports.IATACode == arrival_airport_code)
        )
    ).first()

    departure_airport: Airports = departure_airport_raw[0]
    arrival_airport: Airports = arrival_airport_raw[0]

    if any(x == None for x in [departure_airport, arrival_airport]):
        await exception("aiport not found", 400, user.ID, session)

    airports = [x[0].ID for x in (await session.execute(select(Airports))).all()]

    # routes: list[Routes] = [x[0] for x in (await session.execute(select(Routes))).all()]

    schedules: list[Schedules] = [
        x[0]
        for x in (
            await session.execute(select(Schedules).where(Schedules.Date == date_to))
        ).all()
    ]

    schedules_next: list[Schedules] = [
        x[0]
        for x in (
            await session.execute(
                select(Schedules)
                .where(Schedules.Date >= date_to)
                .where(Schedules.Date <= date_to + timedelta(days=2))
            )
        ).all()
    ]

    airports.remove(departure_airport.ID)
    airports.remove(arrival_airport.ID)

    start = departure_airport.ID
    end = arrival_airport.ID

    for schedule in schedules:
        route = await session.get(Routes, schedule.RouteID)

        if route.DepartureAirportID == start and route.ArrivalAirportID == end:
            result["to"].append(
                {
                    "From": departure_airport.IATACode,
                    "To": arrival_airport.IATACode,
                    "Date": date_to,
                    "Time": schedule.Time,
                    "FlightNumbers": [schedule.FlightNumber],
                    "EconomyPrice": schedule.EconomyPrice,
                    "BusinessPrice": round(schedule.EconomyPrice * 1.35, 4),
                    "FirstClassPrice": round(schedule.EconomyPrice * 1.35 * 1.3, 4),
                    "Stops": 0,
                    "ScheduleIds": [schedule.ID],
                }
            )

        for airport in airports:
            for schedule_next in schedules_next:
                if (
                    schedule_next.Time
                    <= (
                        datetime.combine(date(1, 1, 1), schedule.Time)
                        + timedelta(minutes=route.FlightTime)
                    ).time()
                ):
                    continue

                route1 = await session.get(Routes, schedule_next.RouteID)

                if (
                    route.DepartureAirportID == start
                    and route.ArrivalAirportID == airport
                    and route1.DepartureAirportID == airport
                    and route1.ArrivalAirportID == end
                ):
                    result["to"].append(
                        {
                            "From": departure_airport.IATACode,
                            "To": arrival_airport.IATACode,
                            "Date": date_to,
                            "Time": schedule.Time,
                            "FlightNumbers": [
                                schedule.FlightNumber,
                                schedule_next.FlightNumber,
                            ],
                            "EconomyPrice": schedule.EconomyPrice
                            + schedule_next.EconomyPrice,
                            "BusinessPrice": round(
                                (schedule.EconomyPrice + schedule_next.EconomyPrice)
                                * 1.35,
                                4,
                            ),
                            "FirstClassPrice": round(
                                (schedule.EconomyPrice + schedule_next.EconomyPrice)
                                * 1.35
                                * 1.3,
                                4,
                            ),
                            "Stops": 1,
                            "ScheduleIds": [schedule.ID, schedule_next.ID],
                        }
                    )

    if mode == "to-from":
        if date_from == None:
            await exception("date_from is needed", 400, user.ID, session)

        start, end = end, start

        schedules: list[Schedules] = [
            x[0]
            for x in (
                await session.execute(
                    select(Schedules).where(Schedules.Date == date_from)
                )
            ).all()
        ]

        schedules_next: list[Schedules] = [
            x[0]
            for x in (
                await session.execute(
                    select(Schedules)
                    .where(Schedules.Date >= date_from)
                    .where(Schedules.Date <= date_from + timedelta(days=2))
                )
            ).all()
        ]

        for schedule in schedules:
            route = await session.get(Routes, schedule.RouteID)

            if route.DepartureAirportID == start and route.ArrivalAirportID == end:
                result["from"].append(
                    {
                        "From": departure_airport.IATACode,
                        "To": arrival_airport.IATACode,
                        "Date": date_from,
                        "Time": schedule.Time,
                        "FlightNumbers": [schedule.FlightNumber],
                        "EconomyPrice": schedule.EconomyPrice,
                        "BusinessPrice": round(schedule.EconomyPrice * 1.35, 4),
                        "FirstClassPrice": round(schedule.EconomyPrice * 1.35 * 1.3, 4),
                        "Stops": 0,
                        "ScheduleIds": [schedule.ID],
                    }
                )

            for airport in airports:
                for schedule_next in schedules_next:
                    if (
                        schedule_next.Time
                        <= (
                            datetime.combine(date(1, 1, 1), schedule.Time)
                            + timedelta(minutes=route.FlightTime)
                        ).time()
                    ):
                        continue

                    route1 = await session.get(Routes, schedule_next.RouteID)

                    if (
                        route.DepartureAirportID == start
                        and route.ArrivalAirportID == airport
                        and route1.DepartureAirportID == airport
                        and route1.ArrivalAirportID == end
                    ):
                        result["from"].append(
                            {
                                "From": departure_airport.IATACode,
                                "To": arrival_airport.IATACode,
                                "Date": date_from,
                                "Time": schedule.Time,
                                "FlightNumbers": [
                                    schedule.FlightNumber,
                                    schedule_next.FlightNumber,
                                ],
                                "EconomyPrice": schedule.EconomyPrice
                                + schedule_next.EconomyPrice,
                                "BusinessPrice": round(
                                    (schedule.EconomyPrice + schedule_next.EconomyPrice)
                                    * 1.35,
                                    4,
                                ),
                                "FirstClassPrice": round(
                                    (schedule.EconomyPrice + schedule_next.EconomyPrice)
                                    * 1.35
                                    * 1.3,
                                    4,
                                ),
                                "Stops": 1,
                                "ScheduleIds": [schedule.ID, schedule_next.ID],
                            }
                        )

    return result


@flight_router.get("/search")
async def flight_search(
    departure_airport: str = None,
    arrival_airport: str = None,
    departure_date: date = None,
    flight_number: str = None,
    begin: time = None,
    end: time = None,
    user=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    departure = aliased(Airports, name="arrival")
    arrival = aliased(Airports, name="departure")

    stmt = (
        select(
            Schedules.Date,
            Schedules.Time,
            departure.IATACode.label("FROM"),
            arrival.IATACode.label("TO"),
            Schedules.FlightNumber,
            Aircrafts.Name.label("Aircraft"),
            Schedules.EconomyPrice,
            func.floor(Schedules.EconomyPrice * 1.3).label("BuisnessPrice"),
            func.floor((Schedules.EconomyPrice * 1.3) * 1.35).label("FirstClassPrice"),
            Schedules.Confirmed,
        )
        .where(Schedules.AircraftID == Aircrafts.ID)
        .where(Schedules.RouteID == Routes.ID)
        .where(Routes.DepartureAirportID == departure.ID)
        .where(Routes.ArrivalAirportID == arrival.ID)
    )

    if departure_airport != None:
        stmt = stmt.where(departure.IATACode == departure_airport)

    if arrival_airport != None:
        stmt = stmt.where(arrival.IATACode == arrival_airport)

    if departure_date != None:
        stmt = stmt.where(Schedules.Date == departure_date)

    if flight_number != None:
        stmt = stmt.where(Schedules.FlightNumber == flight_number)

    if begin != None:
        stmt = stmt.where(Schedules.Time >= begin)

    if end != None:
        stmt = stmt.where(Schedules.Time <= end)

    scheduless_raw = (await session.execute(stmt)).all()
    sessions = []

    for schedules_raw in scheduless_raw:
        if schedules_raw:
            sessions.append(schedules_raw._mapping)

    return sessions


@flight_router.post("/confirm")
async def flight_confirm(
    flight_id: int,
    user=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    schedules_for_confirm: Schedules = await session.get(Schedules, flight_id)

    if schedules_for_confirm == None:
        await exception("flight not found", 400, user.ID, session)

    if schedules_for_confirm.Confirmed == 0:
        await session.execute(
            update(Schedules).where(Schedules.ID == flight_id).values(Confirmed=1)
        )
        await session.commit()
        response = {"detail": "flight confirm success"}
    else:
        await session.execute(
            update(Schedules).where(Schedules.ID == flight_id).values(Confirmed=0)
        )
        await session.commit()
        response = {"detail": "flight unconfirm success"}

    return response


@flight_router.post("/edit")
async def flight_edit(
    flight_id: int,
    date: date = None,
    time: time = None,
    economy_price: int = None,
    user=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    flight_to_edit: Schedules = await session.get(Schedules, flight_id)

    if flight_to_edit is None:
        await exception("flight not found", 400, user.ID, session)

    if date:
        flight_to_edit.Date = date
    if time:
        flight_to_edit.Time = time
    if economy_price:
        flight_to_edit.EconomyPrice = economy_price

    await session.commit()

    return {"detail": "flight edit success"}


@flight_router.post("/import")
async def flight_import(
    file: UploadFile = File(...),
    user=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    lines = (await file.read()).decode("utf-8").split("\n")
    stmts = []

    dubles = 0
    not_allowed = 0

    for line in lines:
        data = line.split(",")

        if "OK" in data[8]:
            data[8] = 1
        else:
            data[8] = 0

        if data[0] == "EDIT":
            schedule_raw = (
                await session.execute(
                    select(Schedules)
                    .where(Schedules.Date == data[1])
                    .where(Schedules.FlightNumber == data[3])
                )
            ).first()

            if schedule_raw == None:
                not_allowed += 1
                continue

            schedule: Schedules = schedule_raw[0]

            aircraft = await session.get(Aircrafts, data[6])

            departure_airport_raw = (
                await session.execute(
                    select(Airports).where(Airports.IATACode == data[4])
                )
            ).first()

            arrival_airport_raw = (
                await session.execute(
                    select(Airports).where(Airports.IATACode == data[5])
                )
            ).first()

            if any(
                x == None
                for x in [aircraft, departure_airport_raw, arrival_airport_raw]
            ):
                not_allowed += 1
                continue

            departure_airport: Airports = departure_airport_raw[0]
            arrival_airport: Airports = arrival_airport_raw[0]

            route_raw = (
                await session.execute(
                    select(Routes)
                    .where(Routes.DepartureAirportID == departure_airport.ID)
                    .where(Routes.ArrivalAirportID == arrival_airport.ID)
                )
            ).first()

            if route_raw == None:
                not_allowed += 1
                continue

            route: Routes = route_raw[0]

            schedule_ins = {
                "Date": data[1],
                "Time": data[2],
                "AircraftID": aircraft.ID,
                "RouteID": route.ID,
                "FlightNumber": data[3],
                "EconomyPrice": float(data[7]),
                "Confirmed": data[8],
            }

            stmts.append(
                update(Schedules)
                .where(Schedules.ID == schedule.ID)
                .values(schedule_ins)
            )

        elif data[0] == "ADD":
            schedule_duble = (
                await session.execute(
                    select(Schedules)
                    .where(Schedules.Date == data[1])
                    .where(Schedules.FlightNumber == data[3])
                )
            ).first()

            if schedule_duble != None:
                dubles += 1
                continue

            aircraft = await session.get(Aircrafts, data[6])

            departure_airport_raw = (
                await session.execute(
                    select(Airports).where(Airports.IATACode == data[4])
                )
            ).first()

            arrival_airport_raw = (
                await session.execute(
                    select(Airports).where(Airports.IATACode == data[5])
                )
            ).first()

            if any(
                x == None
                for x in [aircraft, departure_airport_raw, arrival_airport_raw]
            ):
                not_allowed += 1
                continue

            departure_airport: Airports = departure_airport_raw[0]
            arrival_airport: Airports = arrival_airport_raw[0]

            route_raw = (
                await session.execute(
                    select(Routes)
                    .where(Routes.DepartureAirportID == departure_airport.ID)
                    .where(Routes.ArrivalAirportID == arrival_airport.ID)
                )
            ).first()

            if route_raw == None:
                not_allowed += 1
                continue

            route: Routes = route_raw[0]

            schedule_ins = {
                "Date": data[1],
                "Time": data[2],
                "AircraftID": aircraft.ID,
                "RouteID": route.ID,
                "FlightNumber": data[3],
                "EconomyPrice": float(data[7]),
                "Confirmed": data[8],
            }

            stmts.append(insert(Schedules).values(schedule_ins))

        else:
            not_allowed += 1

    if not_allowed > 0:
        await exception(
            f"incorrect import file. number of wrong rows: {not_allowed}",
            400,
            user.ID,
            session,
        )

    for stmt in stmts:
        await session.execute(stmt)

    await session.commit()

    return {"detail": "flight import success", "duplicates": dubles}


@flight_router.get("/export")
async def flight_export(
    begin: date = None,
    end: date = None,
    user=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    try:
        writer = ExcelWriter(f"{EXCEL_PATH}/export.xlsx")

        now = datetime.utcnow() + timedelta(hours=10)
        first_sunday, num_days = calendar.monthrange(now.year, now.month)

        begin_month = (now - timedelta(days=now.day - 1)).date()
        end_month = begin_month + timedelta(days=num_days - 1)

        if begin == None:
            begin = begin_month
        if end == None:
            end = end_month

        departure = aliased(Airports, name="arrival")
        arrival = aliased(Airports, name="departure")

        stmt = (
            select(
                Schedules.FlightNumber.label("Номер рейса"),
                Schedules.Date.label("День вылета"),
                Schedules.Time.label("Время вылета"),
                departure.IATACode.label("Аэропорт вылета"),
                arrival.IATACode.label("Аэропорт прилета"),
                Routes.FlightTime.label("Время полета (мин.)"),
                Aircrafts.Name.label("Самолет"),
                Schedules.EconomyPrice.label("Цена билета (эконом)"),
                func.floor(Schedules.EconomyPrice * 1.3).label("Цена билета (бизнес)"),
                func.floor((Schedules.EconomyPrice * 1.3) * 1.35).label(
                    "Цена билета (первый класс)"
                ),
                Schedules.Confirmed,
            )
            .where(Schedules.AircraftID == Aircrafts.ID)
            .where(Schedules.RouteID == Routes.ID)
            .where(Routes.DepartureAirportID == departure.ID)
            .where(Routes.ArrivalAirportID == arrival.ID)
            .where(Schedules.Date >= begin)
            .where(Schedules.Date <= end)
            .order_by(desc(Schedules.Date))
        )

        flights = (await session.execute(stmt)).all()

        if flights == []:
            flights.append(
                {
                    "Номер рейса": None,
                    "День вылета": None,
                    "Время вылета": None,
                    "Аэропорт вылета": None,
                    "Аэропорт прилета": None,
                    "Время полета (ч.)": None,
                    "Самолет": None,
                    "Цена билета (эконом)": None,
                    "Цена билета (бизнес)": None,
                    "Цена билета (первый класс)": None,
                }
            )

        df = DataFrame(flights)
        df.to_excel(writer, sheet_name="Рейсы", index=False, engine="xlsxwriter")

        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets["Рейсы"].set_column(col_idx, col_idx, column_width + 10)

        writer.close()

        return FileResponse(
            path=f"{EXCEL_PATH}/export.xlsx",
            filename="export.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        await exception(f"smth went wrong: {e}", 400, user.ID, session)
