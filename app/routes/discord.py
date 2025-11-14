from fastapi.requests import Request
import jwt
import os
import openapi_client
from openapi_client.models.user_pii_response import UserPIIResponse
from openapi_client.rest import ApiException
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

load_dotenv()
router = APIRouter()

@router.get("/discord/presence", tags=["discord"])
def get_user_presence(request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")
  
  configuration = openapi_client.Configuration()
  configuration.host = os.getenv('API_ENDPOINT')
  configuration.access_token = (jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256']))['access_token']

  with openapi_client.ApiClient(configuration) as api_client:
    api_instance = openapi_client.DefaultApi(api_client)
    try:
      api_response = api_instance.get_my_user()
      return api_response
    except ApiException as e:
      print("Exception when calling DefaultApi->get_my_user: %s\n" % e)
      raise HTTPException(status_code=500, detail="Failed to fetch presence")

@router.get("/discord/me", tags=["discord"])
def get_user_guilds(request: Request):
  auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
  if not auth_header:
    raise HTTPException(status_code=401, detail="Authorization header missing")
  
  configuration = openapi_client.Configuration()
  configuration.host = os.getenv('API_ENDPOINT')
  configuration.access_token = (jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256']))['access_token']

  with openapi_client.ApiClient(configuration) as api_client:
    api_instance = openapi_client.DefaultApi(api_client)
    try:
      api_response = api_instance.get_my_user()
      return api_response
    except ApiException as e:
      print("Exception when calling DefaultApi->get_my_user: %s\n" % e)
      raise HTTPException(status_code=500, detail="Failed to fetch user")