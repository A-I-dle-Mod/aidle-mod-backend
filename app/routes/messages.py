from app.dependencies import get_db
import jwt
import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

load_dotenv()
router = APIRouter()

@router.get('/message-stats', tags=['me'])
async def get_me(request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")

  db = await get_db()

  token = jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])

  guilds = await db.guild.find_many(
    where={
      "owner_id": token["user_id"]
    },
  )

  guildIds = []

  for x in range(len(guilds)):
    guildIds.append(guilds[x].guild_id)

  messages = await db.message.find_many(
    where={
      "created_date": {
        "gte": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
      },
      "guild_id": {
        "in": guildIds
      }
    },
    include={
      "guild": True
    }
  )

  return {"status": "success", "data": messages}