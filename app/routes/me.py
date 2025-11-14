from app.dependencies import get_db
import jwt
import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

load_dotenv()
router = APIRouter()

@router.get('/me', tags=['me'])
async def get_me(request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")

  db = await get_db()

  token = jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])

  user = await db.user.find_unique(
    where={
      "owner_id": token["user_id"]
    },
    include={
      "plan": True,
      "guilds": True
    }
  )

  return user