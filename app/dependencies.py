import os
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from prisma import Prisma
from dotenv import load_dotenv

load_dotenv()

model = AutoModelForSequenceClassification.from_pretrained(os.getenv("MODEL_PATH"))
tokenizer = AutoTokenizer.from_pretrained(os.getenv("TOKENIZER_PATH"))

def get_model():
  return model

def get_tokenizer():
  return tokenizer

async def get_db():
  db = Prisma()
  await db.connect()
  return db