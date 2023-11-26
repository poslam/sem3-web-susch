from datetime import timedelta
from uuid import uuid4

from config import AUTH_TOKEN_LIFE
from database.database import get_session
from database.models import Roles, Tokens, Users
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils import time

auth_router = APIRouter()


async def type_required(types: list,  auth: str = Header(None),
                        session: AsyncSession = Depends(get_session)):

    token: Tokens = (await session.execute(
        select(Tokens)
        .where(Tokens.Token == auth)
        .where(Tokens.Active == True)
    )).first()

    if token == None:
        raise HTTPException(status_code=401, detail="token is invalid")

    token = token[0]

    if time() - timedelta(hours=int(AUTH_TOKEN_LIFE)) > token.CreateTime:

        await session.execute(
            update(Tokens)
            .where(Tokens.ID == token.ID)
            .values({
                "DeletionTime": time(),
                "Active": False
            })
        )
        await session.commit()

        raise HTTPException(status_code=401, detail="token is invalid")

    user: Users = await session.get(Users, token.UserID)

    if user == None:
        raise HTTPException(status_code=400, detail="user not found")

    role: Roles = await session.get(Roles, user.RoleID)

    if types != []:
        if role.Title not in types:
            raise HTTPException(status_code=400, detail="not allowed")

    return user


async def login_required(auth: str = Header(None),
                         session: AsyncSession = Depends(get_session)):
    return await type_required(["User"], auth, session)


async def user_required(auth: str = Header(None),
                        session: AsyncSession = Depends(get_session)):
    return await type_required([], auth, session)


async def admin_required(auth: str = Header(None),
                         session: AsyncSession = Depends(get_session)):
    return await type_required(["Administrator"], auth, session)


@auth_router.post("/login")
async def login(request: Request,
                session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()

        email = data["email"].lstrip(' ').rstrip(' ')
        password = data["password"].lstrip(' ').rstrip(' ')
    except:
        raise HTTPException(status_code=400, detail="incorrect request")

    user: Users = (await session.execute(
        select(Users)
        .where(Users.Email == email)
    )).first()

    if user == None:
        raise HTTPException(status_code=400, detail='user not found')

    user = user[0]

    if user.Password != password:
        raise HTTPException(status_code=400, detail="wrong auth data")

    role = (await session.get(Roles, user.RoleID)).Title

    token: Tokens = (await session.execute(
        select(Tokens)
        .where(Tokens.UserID == user.ID)
        .where(Tokens.Active == True)
    )).first()

    if token == None:
        pass

    else:
        token = token[0]

        if time() - timedelta(hours=int(AUTH_TOKEN_LIFE)) > token.CreateTime:

            await session.execute(
                update(Tokens)
                .where(Tokens.ID == token.ID)
                .values({
                    "DeletionTime": time(),
                    "Active": False
                })
            )
            await session.commit()

        else:
            return {"token": token.Token,
                    "type": role
                    }

    token = uuid4()

    token_insert = {
        "Token": token,
        "CreateTime": time(),
        "UserID": user.ID,
        "Active": True
    }

    await session.execute(
        insert(Tokens).values(token_insert)
    )
    await session.commit()

    return {"token": token,
            "type": role
            }


@auth_router.post("/logout")
async def logout(user: Users = Depends(user_required),
                 session: AsyncSession = Depends(get_session)):

    await session.execute(
        update(Tokens)
        .where(Tokens.UserID == user.ID)
        .where(Tokens.Active == True)
        .values({
            "DeletionTime": time(),
            "Active": False
        })
    )
    await session.commit()

    return {"detail": "logout success"}
