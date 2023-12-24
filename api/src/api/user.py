from datetime import datetime, timedelta

from database.database import get_session
from database.models import Logs, Offices, Roles, Tokens, Users
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import admin_required, login_required, user_required
from src.utils import exception, time

user_router = APIRouter()


@user_router.get("/view")
async def user_view(type: str = None,  # None, admin
                    office_ids: str = None,
                    begin: datetime = None,
                    end: datetime = None,
                    user: Users = Depends(user_required),
                    session: AsyncSession = Depends(get_session)):

    if type == None:
        
        office = await session.get(Offices, user.OfficeID)
        
        time_in_system = timedelta(hours=0)

        stmt = (select(Tokens.CreateTime, Tokens.DeletionTime, Tokens.Active)
                .where(Tokens.UserID == user.ID))

        stmt1 = (select(Logs)
                 .where(Logs.UserID == user.ID))

        if begin != None:
            stmt = stmt.where(Tokens.CreateTime >= begin)
            stmt1 = stmt.where(Logs.Time >= begin)

        if end != None:
            stmt = stmt.where(Tokens.CreateTime <= end)
            stmt1 = stmt.where(Logs.Time <= end)

        sessions_raw = (await session.execute(stmt)).all()

        sessions = []

        for session_raw in sessions_raw:
            session_ = session_raw._mapping

            if not session_["Active"]:
                session_time = session_[
                    "DeletionTime"] - session_["CreateTime"]
            else:
                session_time = time() - session_["CreateTime"]

            time_in_system += session_time

            sessions.append({
                "login": session_["CreateTime"],
                "logout": session_["DeletionTime"],
                "session_time": session_time
            })

        logs = [x[0] for x in (await session.execute(stmt1)).all()]

        return {
            "first_name": user.FirstName,
            "last_name": user.LastName,
            "email": user.Email,
            "office": office.ID,
            "errors": logs,
            "sessions": sessions,
            "time_in_system": time_in_system
        }

    elif type == "admin":

        stmt = (select(Users.ID,
                       Users.FirstName,
                       Users.LastName,
                       Users.Email,
                       Users.Birthdate,
                       Roles.Title.label("Role"),
                       Offices.Title.label("Office"),
                       Users.Active)
                .where(Users.RoleID == Roles.ID)
                .where(Users.OfficeID == Offices.ID))

        if office_ids != None:
            office_ids_list = [int(id) for id in office_ids.split(',')]
            stmt = stmt.where(Users.OfficeID.in_(office_ids_list))

        users_raw = (await session.execute(stmt))

        users = []

        for user_raw in users_raw:
            user_ = dict(user_raw._mapping)

            user_["Birthdate"] = (
                time().date()-user_["Birthdate"]).days // 365.25

            users.append(user_)

        return users


@user_router.post("/create")
async def user_create(request: Request, user=Depends(admin_required),
                      session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()

        email = data["email"]
        password = data["password"]
        first_name = data["first_name"]
        last_name = data["last_name"]
        office_id = data["office_id"]
        birthdate = data["birthdate"]

    except:
        await exception("incorrect request", 400, user.ID, session)

    user_ = (await session.execute(select(Users).where(Users.Email == email))).first()

    if user_ != None:
        await exception("user already exist", 400, user.ID, session)

    office = await session.get(Offices, office_id)

    if office == None:
        await exception("office not found", 400, user.ID, session)

    try:

        birthdate = datetime.strptime(birthdate, "%Y-%m-%d")

    except:
        await exception("incorrect birthdate format", 400, user.ID, session)

    if birthdate > time():
        await exception("incorrect birthdate", 400, user.ID, session)

    last_id = (await session.execute(select(Users.ID).order_by(desc(Users.ID)))).all()[0]._mapping["ID"]

    user_insert = {
        "ID": last_id+1,
        "Email": email,
        "RoleID": 1,
        "Password": password,
        "FirstName": first_name,
        "LastName": last_name,
        "OfficeID": office_id,
        "Birthdate": birthdate,
    }

    await session.execute(insert(Users).values(user_insert))
    await session.commit()

    return {"detail": "user create success"}


@user_router.post("/ban")
async def user_ban(user_id: int, user=Depends(admin_required),
                   session: AsyncSession = Depends(get_session)):

    user_for_ban: Users = await session.get(Users, user_id)

    if user_for_ban == None:
        await exception("user not found", 400, user.ID, session)

    await session.execute(
        update(Users)
        .where(Users.ID == user_id)
        .values(Active=False)
    )
    await session.commit()

    return {"detail": "user ban success"}


@user_router.post("/edit")
async def user_edit(user_id: int,
                    request: Request, user=Depends(admin_required),
                    session: AsyncSession = Depends(get_session)):

    try:
        data = await request.json()

        email = data["email"]
        password = data["password"]
        role = data["role"]
        first_name = data["first_name"]
        last_name = data["last_name"]
        office_id = data["office_id"]
        birthdate = data["birthdate"]
        active = data["active"]

    except:
        await exception("incorrect request", 400, user.ID, session)

    user_ = await session.get(Users, user_id)

    if user_ == None:
        await exception("user not found", 400, user.ID, session)

    user_ = (await session.execute(select(Users).where(Users.Email == email))).first()

    if user_ != None and user_[0].ID != user_id:
        await exception("user already exist", 400, user.ID, session)

    office = await session.get(Offices, office_id)

    if office == None:
        await exception("office not found", 400, user.ID, session)

    role_db = (await session.execute(select(Roles).where(Roles.Title == role))).first()

    if role_db == None:
        await exception("incorrect role. should be User or Administrator", 400, user.ID, session)

    try:

        birthdate = datetime.strptime(birthdate, "%Y-%m-%d")

    except:
        await exception("incorrect birthdate format", 400, user.ID, session)

    if birthdate > time():
        await exception("incorrect birthdate", 400, user.ID, session)

    user_insert = {
        "Email": email,
        "RoleID": role_db[0].ID,
        "Password": password,
        "FirstName": first_name,
        "LastName": last_name,
        "OfficeID": office_id,
        "Birthdate": birthdate,
        "Active": active
    }

    await session.execute(update(Users).where(Users.ID == user_id).values(user_insert))
    await session.commit()

    return {"detail": "user edit success"}
