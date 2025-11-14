from app.dependencies import get_db
import jwt
import os
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

load_dotenv()

class GuildCreateRequest(BaseModel):
  owner_id: str
  owner_name: str | None = None
  owner_icon: str | None = None
  guild_name: str
  guild_id: str
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
async def get_guilds(guild_id: str, request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")
  
  user_id = (jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256']))['user_id']

  db = await get_db()

  # Fetch all guilds
  guilds = await db.guild.find_unique(
    where={
      "owner_id": user_id,
      "guild_id": guild_id
    },
    include={
      'messages': {
        'take': 20
      }
    }
  )

  settings = await db.settings.find_unique(
    where={
      "guild_id": guilds.guild_id
    }
  )
  
  if not settings:
    settings = await db.settings.create(
      data={
        "guild_id": guilds.guild_id
      }
    )

  guilds.settings = settings


  await db.disconnect()

  return {"status": "success", "guild": guilds}

# This is intended to be called via bot, we may need to add a header to
# Manage this request, so you can't do it willy nilly
@router.delete("/guild/{guild_id}", tags=["guild"])
async def delete_guild(guild_id: str):
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

class Settings(BaseModel):
  confidence_limit: float
  moderation_message: str
  enable_h: bool
  enable_v: bool
  enable_s: bool
  enable_h2: bool
  enable_v2: bool
  enable_s3: bool
  enable_hr: bool
  enable_sh: bool

@router.post("/guild/{guild_id}/settings", tags=["guild"])
async def update_settings(guild_id: str, item: Settings, request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")
  
  user_id = (jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256']))['user_id']

  db = await get_db()

  # Check the user has access to the guild
  guild = await db.guild.find_unique(
    where={
      "owner_id": user_id,
      "guild_id": guild_id
    }
  )

  if not guild:
    raise HTTPException(status_code=401, detail="Unauthorised to access this guild")

  await db.settings.update(
    where={
      "guild_id": guild_id
    },
    data={
      "confidence_limit": item.confidence_limit,
      "moderation_message": item.moderation_message,
      "enable_h": item.enable_h,
      "enable_v": item.enable_v,
      "enable_s": item.enable_s,
      "enable_h2": item.enable_h2,
      "enable_v2": item.enable_v2,
      "enable_s3": item.enable_s3,
      "enable_hr": item.enable_hr,
      "enable_sh": item.enable_sh,
      "updated_date": datetime.now()
    }
  )

  return {"status": "success"}