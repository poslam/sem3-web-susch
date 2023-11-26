from database.database import get_session
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth import admin_required

user_router = APIRouter()


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
        active = data["active"]

    except:
        raise HTTPException(status_code=400, detail="incorrect request")

    # user = (await session.execute(select(Users).where(Users.nickname == nickname))).first()

    # if user != None:
    #     raise HTTPException(status_code=400, detail="nickname already picked")

    # user = {
    #     "nickname": nickname,
    #     "password": generate_password_hash(password),
    # }

    # await session.execute(insert(Users).values(user))
    # await session.commit()

    # return {"detail": "successfully registered"}


@user_router.get("/view")
async def user_view():
    pass