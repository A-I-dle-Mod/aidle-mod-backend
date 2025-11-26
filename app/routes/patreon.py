from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.dependencies import get_db
import jwt
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlencode, quote

load_dotenv()
router = APIRouter()

PATREON_CLIENT_ID = os.getenv('PATREON_CLIENT_ID')
PATREON_CLIENT_SECRET = os.getenv('PATREON_CLIENT_SECRET')
PATREON_REDIRECT_URI = os.getenv('PATREON_REDIRECT_URI', 'http://localhost:8000/patreon/callback')
APP_URL = os.getenv('APP_URL', 'http://localhost')

def get_current_user_id(request: Request) -> str:
    """Extract user ID from JWT token in request header"""
    auth_header = request.headers.get(os.getenv('USER_COOKIE_NAME'))
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    token = jwt.decode(auth_header, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
    return token["user_id"]

async def refresh_patreon_token(refresh_token: str) -> dict:
    """Refresh Patreon access token using refresh token"""
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': PATREON_CLIENT_ID,
        'client_secret': PATREON_CLIENT_SECRET,
    }
    
    response = requests.post('https://www.patreon.com/api/oauth2/token', data=data)
    response.raise_for_status()
    return response.json()

async def get_patreon_identity(access_token: str) -> dict:
    """Get Patreon user identity and membership info"""
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    
    # Request identity with memberships included
    params = {
        'include': 'memberships',
        'fields[member]': 'patron_status,currently_entitled_amount_cents',
    }
    
    response = requests.get(
        'https://www.patreon.com/api/oauth2/v2/identity',
        headers=headers,
        params=params
    )
    response.raise_for_status()
    return response.json()

def check_is_subscriber(identity_data: dict) -> bool:
    """Check if user is an active Patreon subscriber based on identity data"""
    if 'included' not in identity_data:
        return False
    
    # Look through included memberships
    for item in identity_data.get('included', []):
        if item.get('type') == 'member':
            patron_status = item.get('attributes', {}).get('patron_status')
            # Active patron means they're currently subscribed
            if patron_status == 'active_patron':
                return True
    
    return False

@router.get("/patreon/oauth", tags=["patreon"])
async def get_patreon_oauth_url(request: Request):
    """Get Patreon OAuth URL for redirecting user to authorize"""
    get_current_user_id(request)  # Verify user is authenticated
    
    if not PATREON_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Patreon client ID not configured")
    
    # Build OAuth URL
    params = {
        'response_type': 'code',
        'client_id': PATREON_CLIENT_ID,
        'redirect_uri': PATREON_REDIRECT_URI,
        'scope': 'identity identity[email]',
    }
    
    oauth_url = f"https://www.patreon.com/oauth2/authorize?{urlencode(params)}"
    
    return {"oauth_url": oauth_url}

@router.get("/patreon/callback", tags=["patreon"])
async def patreon_callback(code: str, state: str = None):
    """Handle Patreon OAuth callback - redirects back to frontend with code"""
    if not code:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{APP_URL}/patreon/error?error=authorization_code_missing"
        )
    
    # Redirect back to frontend with the authorization code
    # Frontend should then call /patreon/link with this code
    return RedirectResponse(
        url=f"{APP_URL}/patreon/callback?code={code}&state={state or ''}"
    )

@router.post("/patreon/link", tags=["patreon"])
async def link_patreon_account(code: str, request: Request):
    """Link Patreon account to logged-in user"""
    user_id = get_current_user_id(request)
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")
    
    # Exchange code for access token
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': PATREON_REDIRECT_URI,
        'client_id': PATREON_CLIENT_ID,
        'client_secret': PATREON_CLIENT_SECRET,
    }
    
    try:
        response = requests.post('https://www.patreon.com/api/oauth2/token', data=data)
        response.raise_for_status()
        token_data = response.json()
        
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        
        if not access_token:
            raise HTTPException(status_code=500, detail="Failed to get access token")
        
        # Get user identity
        identity_data = await get_patreon_identity(access_token)
        
        # Extract Patreon user ID
        patreon_user_id = identity_data.get('data', {}).get('id')
        if not patreon_user_id:
            raise HTTPException(status_code=500, detail="Failed to get Patreon user ID")
        
        # Check subscription status
        is_subscriber = check_is_subscriber(identity_data)
        
        # Update user in database
        db = await get_db()
        
        # Check if this Patreon account is already linked to another user
        existing_user = await db.user.find_unique(
            where={"patreon_id": patreon_user_id}
        )
        if existing_user and existing_user.owner_id != user_id:
            raise HTTPException(status_code=400, detail="This Patreon account is already linked to another user")
        
        # Update or create user record
        user = await db.user.find_unique(where={"owner_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        await db.user.update(
            where={"owner_id": user_id},
            data={
                "patreon_id": patreon_user_id,
                "patreon_access_token": access_token,
                "patreon_refresh_token": refresh_token,
                "patreon_connected_at": datetime.now(),
                "is_patreon_subscriber": is_subscriber,
            }
        )
        
        return {
            "status": "success",
            "message": "Patreon account linked successfully",
            "is_subscriber": is_subscriber
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error during Patreon linking: {e}")
        raise HTTPException(status_code=500, detail="Patreon linking failed")

@router.delete("/patreon/unlink", tags=["patreon"])
async def unlink_patreon_account(request: Request):
    """Unlink Patreon account from logged-in user"""
    user_id = get_current_user_id(request)
    
    db = await get_db()
    
    user = await db.user.find_unique(where={"owner_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.patreon_id:
        raise HTTPException(status_code=400, detail="No Patreon account linked")
    
    await db.user.update(
        where={"owner_id": user_id},
        data={
            "patreon_id": None,
            "patreon_access_token": None,
            "patreon_refresh_token": None,
            "patreon_connected_at": None,
            "is_patreon_subscriber": False,
        }
    )
    
    return {
        "status": "success",
        "message": "Patreon account unlinked successfully"
    }

@router.get("/patreon/status", tags=["patreon"])
async def get_patreon_status(request: Request):
    """Get current Patreon subscription status and refresh if needed"""
    user_id = get_current_user_id(request)
    
    db = await get_db()
    
    user = await db.user.find_unique(where={"owner_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.patreon_id or not user.patreon_access_token:
        return {
            "linked": False,
            "is_subscriber": False,
            "message": "No Patreon account linked"
        }
    
    try:
        # Try to get current identity with existing token
        try:
            identity_data = await get_patreon_identity(user.patreon_access_token)
            is_subscriber = check_is_subscriber(identity_data)
        except requests.exceptions.HTTPError as e:
            # Token might be expired, try to refresh
            if e.response.status_code == 401 and user.patreon_refresh_token:
                try:
                    token_data = await refresh_patreon_token(user.patreon_refresh_token)
                    new_access_token = token_data.get('access_token')
                    new_refresh_token = token_data.get('refresh_token', user.patreon_refresh_token)
                    
                    identity_data = await get_patreon_identity(new_access_token)
                    is_subscriber = check_is_subscriber(identity_data)
                    
                    # Update tokens in database
                    await db.user.update(
                        where={"owner_id": user_id},
                        data={
                            "patreon_access_token": new_access_token,
                            "patreon_refresh_token": new_refresh_token,
                            "is_patreon_subscriber": is_subscriber,
                        }
                    )
                except Exception as refresh_error:
                    print(f"Error refreshing Patreon token: {refresh_error}")
                    # Mark as not subscriber if refresh fails
                    is_subscriber = False
                    await db.user.update(
                        where={"owner_id": user_id},
                        data={"is_patreon_subscriber": False}
                    )
            else:
                raise
        
        # Update subscription status if it changed
        if user.is_patreon_subscriber != is_subscriber:
            await db.user.update(
                where={"owner_id": user_id},
                data={"is_patreon_subscriber": is_subscriber}
            )
        
        return {
            "linked": True,
            "is_subscriber": is_subscriber,
            "patreon_id": user.patreon_id,
            "connected_at": user.patreon_connected_at.isoformat() if user.patreon_connected_at else None
        }
    
    except Exception as e:
        print(f"Error checking Patreon status: {e}")
        return {
            "linked": True,
            "is_subscriber": False,
            "error": "Failed to verify subscription status"
        }

