from app.dependencies import get_db
import jwt
import os
from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

load_dotenv()

class GuildCreateRequest(BaseModel):
  owner_id: int
  owner_name: str | None = None
  owner_icon: str | None = None
  guild_name: str
  guild_id: int
  guild_icon: str | None = None
  moderate: bool = True

router = APIRouter()

@router.post("/guild", tags=["guild"])
async def create_guild(item: GuildCreateRequest):
  db = await get_db()

  # Check if user exists
  user = await db.user.find_unique(where={"owner_id": item.owner_id})
  print("Found user:", user)

  if not user:
    print("User not found, creating new user.")
    # Create new user
    user = await db.user.create(
      data={
        "owner_id": item.owner_id,
        "owner_name": item.owner_name,
        "owner_icon": item.owner_icon,
        "plan": {
          "create": {
            "max_requests": 100
          }
        }
      }
    )

  # Create new guild
  guild = await db.guild.find_unique(where={"guild_id": item.guild_id})

  if not guild:
    guild = await db.guild.create(
      data={
        "guild_name": item.guild_name,
        "guild_id": item.guild_id,
        "guild_icon": item.guild_icon,
        "moderate": item.moderate,
        "owner_id": user.owner_id
      }
    )
  else:
    await db.guild.update(
      data={
        "moderate": True
      },
      where={"guild_id": item.guild_id}
    )

  settings = await db.guild.find_unique(where={"guild_id": item.guild_id})

  if not settings:
    settings = await db.settings.create(
      data={
        "guild_id": item.guild_id
      }
    )

  await db.guild.update(
    data={
      "settings_id": settings.id
    },
    where={
      "guild_id": guild.id
    }
  )

  await db.disconnect()

  return {"status": "success", "guild_id": guild.guild_id}

@router.get("/guilds", tags=["guild"])
async def get_guilds(request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")
  
  user_id = (jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256']))['user_id']

  db = await get_db()

  # Fetch all guilds
  guilds = await db.guild.find_many(
    where={
      "owner_id": user_id,
      "moderate": True
    },
    include={
      'messages': True
    }
  )

  await db.disconnect()

  return {"status": "success", "guilds": guilds}

@router.get("/guilds/{guild_id}", tags=["guild"])
async def get_guilds(guild_id: int, request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")
  
  user_id = (jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256']))['user_id']

  db = await get_db()
  print(user_id)

  # Fetch all guilds
  guilds = await db.guild.find_unique(
    where={
      "owner_id": user_id,
      "guild_id": guild_id
    },
    include={
      'messages': True,
      'settings': True
    }
  )
  print(guild_id)

  await db.disconnect()

  return {"status": "success", "guild": guilds}

@router.delete("/guild/{guild_id}", tags=["guild"])
async def delete_guild(guild_id: int):
  db = await get_db()

  # Delete guild
  deleted_guild = await db.guild.update(
    data={
      'moderate': False
    },
    where={"guild_id": guild_id}
  )

  await db.disconnect()

  return {"status": "success", "deleted_guild_id": deleted_guild.guild_id}