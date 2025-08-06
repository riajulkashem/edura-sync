# services/api_auth.py
"""
API authentication and JWT token management.
Handles JWT token lifecycle and authentication requests.
"""

import base64
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.exceptions import (
    APICallError,
    APIAuthenticationError,
    APINetworkError,
)


class JWTTokenManager:
    """Manages JWT access and refresh tokens with automatic refresh logic."""

    def __init__(self, security):
        self.security = security
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.logger = logging.getLogger(__name__)

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """Set JWT tokens and calculate expiration time."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        # Calculate expiration time from current time + expires_in seconds
        self.expires_at = datetime.now() + timedelta(seconds=expires_in)

    def get_valid_access_token(self) -> Optional[str]:
        """Get access token if it's still valid (5 minutes buffer)."""
        if not self.access_token or not self.expires_at:
            return None
        
        # Check if token expires within 5 minutes
        buffer_time = datetime.now() + timedelta(minutes=5)
        if self.expires_at <= buffer_time:
            return None
        
        return self.access_token

    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token."""
        return self.refresh_token

    def clear_tokens(self):
        """Clear all stored tokens."""
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

    def is_token_valid(self) -> bool:
        """Check if access token is still valid."""
        return self.get_valid_access_token() is not None

    def _decode_jwt_payload(self, token: str) -> Optional[dict]:
        """Decode JWT token payload to extract expiration time."""
        try:
            # Split JWT token into parts
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None

    def calculate_expires_in(self, access_token: str) -> int:
        """Calculate expires_in from JWT token payload."""
        payload = self._decode_jwt_payload(access_token)
        if payload and 'exp' in payload:
            # exp is Unix timestamp
            exp_timestamp = payload['exp']
            current_timestamp = datetime.now().timestamp()
            expires_in = int(exp_timestamp - current_timestamp)
            return max(expires_in, 0)  # Ensure non-negative
        return 3600  # Default to 1 hour if can't decode


class APIAuthentication:
    """Handles API authentication and request management."""

    def __init__(self, token_manager: JWTTokenManager):
        self.token_manager = token_manager
        self.logger = logging.getLogger(__name__)

    def parse_response(self, response: requests.Response) -> Dict[str, str]:
        """Parse response from API."""
        data = response.json()
        if "data" in data:
            return data.get("data")
        if "results" in data:
            return data.get("results")
        return data

    def authenticate_with_jwt(self, url: str, username: str, password: str) -> Dict[str, str]:
        """
        Authenticate with JWT tokens using username and password.
        
        Args:
            url: Base API URL
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            Dict containing access_token, refresh_token, and expires_in
            
        Raises:
            APIAuthenticationError: If authentication fails
            APINetworkError: If network issues occur
        """
        try:
            self.logger.debug(f"Authenticating with JWT at {url}")
            
            # Prepare authentication data
            auth_data = {
                "username": username,
                "password": password
            }
            
            # Make authentication request
            auth_url = f"{url.rstrip('/')}/api/token/"
            response = requests.post(auth_url, json=auth_data, timeout=10)
            
            if response.status_code == 200:
                token_data = self.parse_response(response)
                
                # Validate required fields
                required_fields = ["access", "refresh"]
                for field in required_fields:
                    if field not in token_data:
                        raise APIAuthenticationError(f"Missing required field: {field}")
                
                # Calculate expires_in if not provided
                if "expires_in" not in token_data:
                    token_data["expires_in"] = self.token_manager.calculate_expires_in(token_data["access"])
                
                self.logger.info("JWT authentication successful")
                return {
                    "access_token": token_data["access"],
                    "refresh_token": token_data["refresh"],
                    "expires_in": token_data.get("expires_in", 3600)
                }
            else:
                error_msg = f"Authentication failed with status {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", error_msg)
                    except:
                        error_msg = f"{error_msg}: {response.text}"
                
                raise APIAuthenticationError(error_msg)
                
        except requests.exceptions.ConnectionError as e:
            raise APINetworkError(f"Network connection error: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise APINetworkError(f"Request timeout: {str(e)}")
        except requests.RequestException as e:
            raise APINetworkError(f"Request failed: {str(e)}")
        except Exception as e:
            raise APICallError(f"Unexpected error during authentication: {str(e)}")

    def refresh_jwt_token(self, url: str) -> bool:
        """
        Refresh JWT access token using refresh token.
        
        Args:
            url: Base API URL
            
        Returns:
            bool: True if refresh successful, False otherwise
        """
        try:
            refresh_token = self.token_manager.get_refresh_token()
            if not refresh_token:
                self.logger.warning("No refresh token available")
                return False
            
            self.logger.debug("Refreshing JWT token")
            
            # Prepare refresh data
            refresh_data = {
                "refresh": refresh_token
            }
            
            # Make refresh request
            refresh_url = f"{url.rstrip('/')}/api/token/refresh/"
            response = requests.post(refresh_url, json=refresh_data, timeout=10)
            
            if response.status_code == 200:
                token_data = self.parse_response(response)
                
                if "access" in token_data:
                    # Update tokens
                    expires_in = self.token_manager.calculate_expires_in(token_data["access"])
                    self.token_manager.set_tokens(
                        token_data["access"],
                        refresh_token,  # Keep existing refresh token
                        expires_in
                    )
                    
                    self.logger.info("JWT token refreshed successfully")
                    return True
                else:
                    self.logger.error("Refresh response missing access token")
                    return False
            else:
                self.logger.error(f"Token refresh failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error refreshing JWT token: {e}")
            return False

    def get_valid_jwt_token(self, url: str, username: str, password: str) -> Optional[str]:
        """
        Get a valid JWT access token, refreshing if necessary.
        
        Args:
            url: Base API URL
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            Optional[str]: Valid access token or None if failed
        """
        try:
            # Check if we have a valid token
            access_token = self.token_manager.get_valid_access_token()
            if access_token:
                return access_token
            
            # Try to refresh existing token
            if self.token_manager.get_refresh_token():
                if self.refresh_jwt_token(url):
                    return self.token_manager.get_valid_access_token()
            
            # Perform fresh authentication
            token_data = self.authenticate_with_jwt(url, username, password)
            self.token_manager.set_tokens(
                token_data["access_token"],
                token_data["refresh_token"],
                token_data["expires_in"]
            )
            
            return self.token_manager.get_valid_access_token()
            
        except Exception as e:
            self.logger.error(f"Failed to get valid JWT token: {e}")
            return None

    def make_authenticated_request(
        self, 
        method: str, 
        url: str, 
        json_data: dict = None,
        username: str = None,
        password: str = None
    ) -> requests.Response:
        """
        Execute an authenticated HTTP request with automatic JWT token handling.
        
        Args:
            method: HTTP method ('GET' or 'POST')
            url: Request URL
            json_data: JSON payload for POST requests
            username: Username for authentication (if needed)
            password: Password for authentication (if needed)
            
        Returns:
            requests.Response: The HTTP response object
            
        Raises:
            APINetworkError: For network-related errors
            APICallError: For other API-related errors
        """
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            # Get valid JWT token
            access_token = self.token_manager.get_valid_access_token()
            if not access_token:
                raise APIAuthenticationError("No valid access token available")
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            # Make request
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=json_data, headers=headers, timeout=10)
            else:
                raise APICallError(f"Unsupported HTTP method: {method}")
            
            # Handle token expiration
            if response.status_code == 401:
                self.logger.warning("Access token expired, attempting refresh")
                if self.refresh_jwt_token(url):
                    # Retry request with new token
                    access_token = self.token_manager.get_valid_access_token()
                    headers["Authorization"] = f"Bearer {access_token}"
                    
                    if method.upper() == "GET":
                        response = requests.get(url, headers=headers, timeout=10)
                    elif method.upper() == "POST":
                        response = requests.post(url, json=json_data, headers=headers, timeout=10)
            
            return response
            
        except requests.exceptions.ConnectionError as e:
            raise APINetworkError(f"Network connection error: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise APINetworkError(f"Request timeout: {str(e)}")
        except requests.RequestException as e:
            raise APINetworkError(f"Request failed: {str(e)}")
        except Exception as e:
            raise APICallError(f"Unexpected error during API request: {str(e)}") 