"""
Shared X.com API client for OAuth 1.0a authenticated requests
"""
import requests
from requests_oauthlib import OAuth1
from typing import Dict, Any, Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


class XAPIClient:
    """Client for making authenticated requests to X.com API"""

    def __init__(self):
        """Initialize the client with OAuth 1.0a credentials"""
        self.auth = OAuth1(
            settings.x_api_key,
            client_secret=settings.x_api_key_secret,
            resource_owner_key=settings.x_access_token,
            resource_owner_secret=settings.x_access_token_secret
        )
        self.base_url = "https://api.twitter.com"

    def post(self, endpoint: str, json_data: Dict[str, Any], timeout: int = 30) -> requests.Response:
        """
        Make a POST request to X.com API

        Args:
            endpoint: API endpoint path (e.g., "/2/notes")
            json_data: JSON payload to send
            timeout: Request timeout in seconds

        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(
            "Making POST request to X.com API",
            endpoint=endpoint,
            payload_keys=list(json_data.keys())
        )

        response = requests.post(
            url,
            json=json_data,
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )

        if not response.ok:
            logger.error(
                "X.com API request failed",
                endpoint=endpoint,
                status_code=response.status_code,
                response=response.text[:500]
            )
        else:
            logger.info(
                "X.com API request successful",
                endpoint=endpoint,
                status_code=response.status_code
            )

        return response

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> requests.Response:
        """
        Make a GET request to X.com API

        Args:
            endpoint: API endpoint path
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(
            "Making GET request to X.com API",
            endpoint=endpoint,
            params=params
        )

        response = requests.get(
            url,
            params=params,
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )

        if not response.ok:
            logger.error(
                "X.com API request failed",
                endpoint=endpoint,
                status_code=response.status_code,
                response=response.text[:500]
            )
        else:
            logger.info(
                "X.com API request successful",
                endpoint=endpoint,
                status_code=response.status_code
            )

        return response


# Singleton instance
_client: Optional[XAPIClient] = None


def get_x_api_client() -> XAPIClient:
    """Get or create the singleton X.com API client"""
    global _client
    if _client is None:
        _client = XAPIClient()
    return _client