import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import jwt
from .routes import moderation
from .routes import guild
from .routes import auth
from .routes import discord
from .routes import me
from .routes import messages
from .routes import test
from .routes import patreon

api = FastAPI()
load_dotenv()

origins = [
  os.getenv("APP_URL", "http://localhost"),
]

api.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

api.include_router(moderation.router)
api.include_router(guild.router)
api.include_router(auth.router)
api.include_router(discord.router)
api.include_router(me.router)
api.include_router(messages.router)
api.include_router(test.router)
api.include_router(patreon.router)

@api.get("/")
async def root():
  return {"message": "Welcome to the Text Moderation API"}