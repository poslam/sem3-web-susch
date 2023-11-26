from database.database import base
from sqlalchemy import (DATE, TEXT, TIME, TIMESTAMP, Boolean, Column,
                        ForeignKey, Integer, String)


class Roles(base):
    __tablename__ = "roles"
    ID = Column(Integer, primary_key=True)
    Title = Column(TEXT)


class CabinTypes(base):
    __tablename__ = "cabintypes"
    ID = Column(Integer, primary_key=True)
    Name = Column(TEXT)


class Countries(base):
    __tablename__ = "countries"
    ID = Column(Integer, primary_key=True)
    Name = Column(TEXT)


class Offices(base):
    __tablename__ = "client"

    ID = Column(Integer, primary_key=True)

    CountryID = Column(ForeignKey(Countries.ID))

    Title = Column(TEXT)
    Phone = Column(String(20))
    Contact = Column(TEXT)


class Users(base):
    __tablename__ = "users"

    ID = Column(Integer, primary_key=True)

    RoleID = Column(ForeignKey(Roles.ID))
    OfficeID = Column(ForeignKey(Offices.ID))

    Email = Column(TEXT)
    Password = Column(TEXT)

    Firstname = Column(TEXT)
    Lastname = Column(TEXT)
    Birthdate = Column(TIMESTAMP)

    Active = Column(Boolean, default=True)


class Tokens(base):
    __tablename__ = "tokens"
    
    ID = Column(Integer, primary_key=True)
    Token = Column(TEXT)
    
    CreateTime = Column(TIMESTAMP)
    DeletionTime = Column(TIMESTAMP)
    
    Active = Column(Boolean)
    UserID = Column(ForeignKey(Users.ID))


class Airports(base):
    __tablename__ = "airports"

    ID = Column(Integer, primary_key=True)

    CountryID = Column(ForeignKey(Countries.ID))
    IATACode = Column(String(20))
    Name = Column(TEXT)


class Aircrafts(base):
    __tablename__ = "aircrafts"

    ID = Column(Integer, primary_key=True)

    Name = Column(TEXT)
    MakeModel = Column(TEXT)

    TotalSeats = Column(Integer)
    EconomySeats = Column(Integer)
    BusinessSeats = Column(Integer)


class Routes(base):
    __tablename__ = "routes"

    ID = Column(Integer, primary_key=True)

    DepartureAirportID = Column(ForeignKey(Airports.ID))
    ArrivalAirportID = Column(ForeignKey(Airports.ID))

    Distance = Column(Integer)
    FlightTime = Column(Integer)


class Schedules(base):
    __tablename__ = "schedules"

    ID = Column(Integer, primary_key=True)

    Date = Column(DATE)
    Time = Column(TIME)

    AircraftID = Column(ForeignKey(Aircrafts.ID))
    RouteID = Column(ForeignKey(Routes.ID))

    FlightNumber = Column(TEXT)
    EconomyPrice = Column(Integer)

    Confirmed = Column(Integer)


class Tickets(base):
    __tablename__ = "tickets"

    ID = Column(Integer, primary_key=True)

    UserID = Column(ForeignKey(Users.ID))
    ScheduleID = Column(ForeignKey(Schedules.ID))
    CabinTypeID = Column(ForeignKey(CabinTypes.ID))

    Firstname = Column(TEXT)
    Lastname = Column(TEXT)

    Phone = Column(String(20))
    PassportNumber = Column(TEXT)
    PassportCountryID = Column(ForeignKey(Countries.ID))
    BookingReference = Column(TEXT)

    Confirmed = Column(Integer)


class Amenities(base):
    __tablename__ = "amenities"

    ID = Column(Integer, primary_key=True)

    Service = Column(TEXT)
    Price = Column(Integer)


class AmenitiesCabinType(base):
    __tablename__ = "amenitiescabintype"

    AmenitiesID = Column(ForeignKey(Amenities.ID), primary_key=True)
    CabinTypeID = Column(ForeignKey(CabinTypes.ID), primary_key=True)


class AmenitiesTickets(base):
    __tablename__ = "amenitiestickets"

    AmenitiesID = Column(ForeignKey(Amenities.ID), primary_key=True)
    TicketID = Column(ForeignKey(Tickets.ID), primary_key=True)

    Price = Column(Integer)
