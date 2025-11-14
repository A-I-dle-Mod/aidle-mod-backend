from fastapi.responses import Response
import requests
import jwt
import os
import openapi_client
from openapi_client.models.user_pii_response import UserPIIResponse
from openapi_client.rest import ApiException
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

load_dotenv()
router = APIRouter()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

@router.post("/auth", tags=["auth"])
def authenticate(code, redirect_uri):
  data = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': redirect_uri
  }
  headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
  }

  responseHeaders = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': os.getenv('APP_URL'),
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Credentials': 'true'
  }

  try:
    r = requests.post('%s/oauth2/token' % os.getenv('API_ENDPOINT'), data=data, headers=headers, auth=(client_id, client_secret))
    r.raise_for_status()
    body = r.json()

    configuration = openapi_client.Configuration()
    configuration.host = os.getenv('API_ENDPOINT')
    configuration.access_token = body['access_token']

    with openapi_client.ApiClient(configuration) as api_client:
      api_instance = openapi_client.DefaultApi(api_client)
      try:
        body['user_id'] = (api_instance.get_my_user()).id
      except ApiException as e:
        print("Exception when calling DefaultApi->get_my_user: %s\n" % e)
        raise HTTPException(status_code=500, detail="Failed to fetch user")
    
    response = Response(content=jwt.encode(body, os.getenv('JWT_SECRET_KEY'), algorithm='HS256'), headers=responseHeaders)
    return response
  except requests.exceptions.RequestException as e:
    print(f"Error during authentication: {e}")
    raise HTTPException(status_code=500, detail="Authentication failed")