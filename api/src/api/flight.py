from datetime import  date, time
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select , func, update
from sqlalchemy.orm import aliased 
from sqlalchemy.sql import label
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils import exception
from src.api.auth import admin_required, login_required
from database.database import get_session
from database.models import Aircrafts, Airports, Schedules, Routes, Users
import math

flight_router = APIRouter()

@flight_router.get("/search")
async def flight_search(departure_airport: str = None,
                        arrival_airport: str = None,
                        departure_date: date = None,
                        flight_number: str = None,
                        begin: time = None,
                        end: time = None,
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
                    func.floor(Schedules.EconomyPrice * 1.3).label('BuisnessPrice'),
                    func.floor((Schedules.EconomyPrice * 1.3) * 1.35).label('FirstClassPrice'),
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
            return {"message": "No flight schedules found."}    
        
@flight_router.post("/confirm")
async def flight_confirm(schedules_id: int,
                         user=Depends(admin_required),
                         session: AsyncSession = Depends(get_session)):
    
    schedules_for_confirm: Schedules = await session.get(Schedules, schedules_id)

    if schedules_for_confirm == None:
        await exception("Schedule not found", 400, user.ID, session)
    
    response = {" ":" "}
    
    if(schedules_for_confirm.Confirmed == 0):
        await session.execute(
        update(Schedules)
        .where(Schedules.ID == schedules_id)
        .values(Confirmed = 1)
        )
        await session.commit()
        response = {"details":"Schedule confirmed"}
    else:
        await session.execute(
        update(Schedules)
        .where(Schedules.ID == schedules_id)
        .values(Confirmed = 0)
        )
        await session.commit()
        response = {"details":"Schedule unconfirmed"}    
    
    return response
        

@flight_router.put("/edit/{flight_id}")
async def edit_flight_schedule(flight_id: int, 
               new_date: date = None,
               new_time: time = None,
               new_economy_price: int = None,
               session: AsyncSession = Depends(get_session)):
    
    flight_to_edit: Schedules = await session.get(Schedules, flight_id)
    
    if flight_to_edit is None:
        return {"error": "Flight schedule not found"}
    
    if new_date:
        flight_to_edit.Date = new_date
    if new_time:
        flight_to_edit.Time = new_time
    if new_economy_price:
        flight_to_edit.EconomyPrice = new_economy_price
    
    await session.commit()
    return {"details": "Flight schedule updated successfully"}        
        



@flight_router.post("/import")
async def import_flights_from_txt(file: UploadFile = File(...), 
                                  session: AsyncSession = Depends(get_session)):
    # Чтение данных из загруженного файла и обработка импорта
    file_data = await file.read()
    decoded_file_data = file_data.decode('utf-8')
    lines = decoded_file_data.split('\n')
    
    dubles = 0
    allowed = 0
    not_allowed = 0
    for line in lines:
        data = line.split(',')
        if len(data) == 9 and data[0] == 'EDIT':
            try:
                existing_schedule: Schedules = await session.get(Schedules, data[1] & data[3])
                existing_routes: Routes = await session.get(Routes,existing_schedule.RouteID)
                existing_ar_airports: Airports = await session.get(Airports,existing_routes.ArrivalAirportID)
                existing_dp_airports: Airports = await session.get(Airports,existing_routes.DepartureAirportID)
                
                if existing_schedule:
                    if data[2]:
                        existing_schedule.Time = data[2]
                    if data[4]:
                        existing_dp_airports.IATACode = data[4]
                    if data[5]:
                        existing_ar_airports.IATACode = data[5]
                    if data[6]:
                        existing_schedule.AircraftID = data[6]
                    if data[7]:
                        existing_schedule.EconomyPrice = data[7]
                    if data[8]:
                        existing_schedule.Confirmed = data[8]   
                    allowed = allowed + 1        
            except IntegrityError:
                dubles = dubles + 1
                
        elif len(data) == 9 and data[0] == 'ADD':
            try:
                new_airports_ar = Airports(IATACode = data[5])
                new_airports_dp = Airports(IATACode = data[4])
                new_routes = Routes(ArrivalAirportID = new_airports_ar.ID, DepartureAirportID = new_airports_dp.ID)
                new_schedule = Schedules(Date=data[1], Time=data[2], EconomyPrice=int(data[7]), FlightNumber=data[3], Confirmed=int(data[8]), RouteID = new_routes.ID)

                session.add(new_airports_ar)
                session.add(new_airports_dp)
                session.add(new_routes)
                session.add(new_schedule)
                allowed = allowed + 1
            except IntegrityError:
                dubles = dubles + 1
        else:
            not_allowed = not_allowed + 1

    await session.commit()
    return {"details" : "Рейсы были успешно импортированы и обработаны.","Allowed": allowed,"Duplicates" : dubles, "Missing Fields" : not_allowed}
 