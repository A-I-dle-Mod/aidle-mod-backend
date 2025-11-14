from app.dependencies import get_model, get_tokenizer, get_db
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class ModerationRequestMetaData(BaseModel):
  message_id: int
  author_id: int
  author_name: str
  guild_id: str

class ModerationRequest(BaseModel):
  input_text: str
  metadata: ModerationRequestMetaData

router = APIRouter()

@router.post("/moderate", tags=["moderation"])
async def moderate_text(item: ModerationRequest):
  db = await get_db()

  metadata = item.metadata

  # Check to see if they've hit their plan limit
  guild = await db.guild.find_unique(
    where={
      "guild_id": metadata.guild_id
    },
    include={
      "owner": True
    }
  )

  settings = await db.settings.find_unique(
    where={
      "guild_id": metadata.guild_id
    }
  )
  
  owner = guild.owner

  plan = await db.plan.find_unique(
    where={
      "id": owner.plan_id
    }
  )

  all_guilds = await db.guild.find_many(
    where={
      "owner_id": owner.owner_id
    }
  )
  guildIds = []

  for x in range(len(all_guilds)):
    guildIds.append(all_guilds[x].guild_id)

  messages = await db.message.find_many(
    where={
      "created_date": {
        "gte": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
      },
      "guild_id": {
        "in": guildIds
      }
    }
  )

  if len(messages) + 1 > plan.max_requests:
    raise HTTPException(status_code=429, detail="You are rate limited until midnight.")

  model = get_model()
  tokenizer = get_tokenizer()

  # Run the model on the input text
  inputs = tokenizer(item.input_text, return_tensors="pt")
  outputs = model(**inputs)

  # Get the predicted logits
  logits = outputs.logits

  # Apply softmax to get probabilities (scores)
  probabilities = logits.softmax(dim=-1).squeeze()

  # Retrieve the labels
  id2label = model.config.id2label
  labels = [id2label[idx] for idx in range(len(probabilities))]

  # Combine labels and probabilities, then sort
  label_prob_pairs = list(zip(labels, probabilities))
  label_prob_pairs.sort(key=lambda item: item[1], reverse=True) 

  total_probability = 0
  simpleSettings = {
    "enable_ok": False,
    "enable_h": settings.enable_h,
    "enable_v": settings.enable_v,
    "enable_s": settings.enable_s,
    "enable_h2": settings.enable_h2,
    "enable_v2": settings.enable_v2,
    "enable_s3": settings.enable_s3,
    "enable_hr": settings.enable_hr,
    "enable_sh": settings.enable_sh,
  }
  confidence_limit = settings.confidence_limit
  for label, probability in label_prob_pairs:
    if label != "OK" and simpleSettings["enable_" + label.lower()] == True:
      total_probability += float(probability)

  # Prepare the response
  response = [{"label": label, "probability": float(probability)} for label, probability in label_prob_pairs]

  # Store the response in the database
  await db.message.create(
    data={
      "message_id": metadata.message_id,
      "guild_id": metadata.guild_id,
      "author_id": metadata.author_id,
      "author_name": metadata.author_name,
      "score": total_probability
    }
  )

  return {
    "results": response,
    "moderate": True if total_probability >= (confidence_limit / 100) else False,
    "moderation_message": settings.moderation_message
  }