import os
import requests
from requests_oauthlib import OAuth1
from typing import Dict, Optional
from app.config import settings

def get_oauth1_headers(url: str, method: str = "GET", body: Optional[str] = None) -> Dict[str, str]:
    """
    Get OAuth 1.0a headers for Twitter/X API requests
    
    Args:
        url: The API endpoint URL
        method: HTTP method (GET, POST, etc.)
        body: Request body (not used in OAuth signature calculation)
    
    Returns:
        Dictionary containing the Authorization header
    """
    # Get credentials from environment variables
    consumer_key = settings.x_api_key
    consumer_secret = settings.x_api_key_secret
    access_token = settings.x_access_token
    access_token_secret = settings.x_access_token_secret
    
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise ValueError("Missing OAuth credentials in environment variables")
    
    # Create OAuth1 auth object
    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
        signature_method='HMAC-SHA1'
    )
    
    # Create a temporary request to get the auth header
    from requests import Request
    req = Request(method, url)
    prepped = req.prepare()
    
    # Apply OAuth1 signature
    signed_req = auth(prepped)
    
    return {"Authorization": signed_req.headers["Authorization"]}


def validate_oauth1_tokens() -> bool:
    """
    Validate OAuth 1.0a tokens by making a test API call
    
    Returns:
        True if tokens are valid, False otherwise
    """
    consumer_key = settings.x_api_key # os.getenv('X_API_KEY')
    consumer_secret = settings.x_api_key_secret # os.getenv('X_API_KEY_SECRET')
    access_token = settings.x_access_token # os.getenv('X_ACCESS_TOKEN')
    access_token_secret = settings.x_access_token_secret # os.getenv('X_ACCESS_TOKEN_SECRET')
    
    try:
        # Create OAuth1 auth object
        auth = OAuth1(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
            signature_method='HMAC-SHA1'
        )
        
        response = requests.get(
            "https://api.twitter.com/2/users/me",
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.ok:
            user_data = response.json()
            print("\n✅ OAuth1 tokens are valid!")
            print(f"Authenticated as: @{user_data['data']['username']}")
            return user_data
        else:
            print("\n❌ OAuth1 tokens are invalid!")
            print(f"Response status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error details: {response.text}")
            return False
    
    except Exception as error:
        print(f"\n❌ Error validating OAuth1 tokens: {error}")
        return False