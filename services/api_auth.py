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
    """Manages authentication tokens for desktop login API."""

    def __init__(self, security):
        self.security = security
        self.auth_token = None  # Simple token from desktop login
        self.institute_id = None
        self.institute_name = None
        self.expires_at = None
        self.logger = logging.getLogger(__name__)

    def set_auth_token(self, token: str, institute_id: str = None, institute_name: str = None):
        """Set authentication token from desktop login."""
        self.auth_token = token
        self.institute_id = institute_id
        self.institute_name = institute_name
        # For now, assume token doesn't expire (server will handle validation)
        # In future, could add expiration handling if server provides it
        self.expires_at = None

    def get_valid_auth_token(self) -> Optional[str]:
        """Get valid authentication token."""
        return self.auth_token

    def clear_tokens(self):
        """Clear all stored tokens."""
        self.auth_token = None
        self.institute_id = None
        self.institute_name = None
        self.expires_at = None

    def is_token_valid(self) -> bool:
        """Check if auth token is available."""
        return self.auth_token is not None

    def get_institute_info(self) -> Dict[str, str]:
        """Get institute information from login."""
        return {
            "institute_id": self.institute_id or "",
            "institute_name": self.institute_name or ""
        }


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

    def authenticate_with_desktop_login(self, url: str, username: str, password: str, sync_id: str) -> Dict[str, str]:
        """
        Authenticate with desktop login endpoint using username, password, and sync_id.
        
        Args:
            url: Base API URL
            username: Username for authentication
            password: Password for authentication
            sync_id: Institute sync ID
            
        Returns:
            Dict containing token, user_id, username, institute_id, and institute_name
            
        Raises:
            APIAuthenticationError: If authentication fails
            APINetworkError: If network issues occur
        """
        try:
            self.logger.debug(f"Authenticating with desktop login at {url}")
            
            # Prepare authentication data
            auth_data = {
                "username": username,
                "password": password,
                "sync_id": sync_id
            }
            
            # Make authentication request
            from core.constants import API_ENDPOINTS
            auth_url = f"{url.rstrip('/')}{API_ENDPOINTS['DESKTOP_LOGIN']}"
            response = requests.post(auth_url, json=auth_data, timeout=10)
            
            if response.status_code == 200:
                login_data = self.parse_response(response)
                
                # Validate required fields
                required_fields = ["token", "user_id", "username", "institute_id", "institute_name"]
                for field in required_fields:
                    if field not in login_data:
                        raise APIAuthenticationError(f"Missing required field: {field}")
                
                self.logger.info(f"Desktop login successful for user: {login_data['username']} at institute: {login_data['institute_name']}")
                return {
                    "token": login_data["token"],
                    "user_id": login_data["user_id"],
                    "username": login_data["username"],
                    "institute_id": str(login_data["institute_id"]),
                    "institute_name": login_data["institute_name"]
                }
            else:
                error_msg = f"Desktop login failed with status {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", error_data.get("message", error_msg))
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

# Remove the refresh_jwt_token method as it's not needed for token-based auth

    def get_valid_auth_token(self, url: str, username: str, password: str, sync_id: str) -> Optional[str]:
        """
        Get a valid authentication token using desktop login.
        
        Args:
            url: Base API URL
            username: Username for authentication
            password: Password for authentication
            sync_id: Institute sync ID
            
        Returns:
            Optional[str]: Valid authentication token or None if failed
        """
        try:
            # Check if we have a valid token
            auth_token = self.token_manager.get_valid_auth_token()
            if auth_token:
                return auth_token
            
            # Perform desktop login authentication
            login_data = self.authenticate_with_desktop_login(url, username, password, sync_id)
            self.token_manager.set_auth_token(
                login_data["token"],
                login_data["institute_id"],
                login_data["institute_name"]
            )
            
            return self.token_manager.get_valid_auth_token()
            
        except Exception as e:
            self.logger.error(f"Failed to get valid auth token: {e}")
            return None

    def make_authenticated_request(
        self, 
        method: str, 
        url: str, 
        json_data: dict = None,
        username: str = None,
        password: str = None,
        sync_id: str = None
    ) -> requests.Response:
        """
        Execute an authenticated HTTP request with token-based authentication.
        
        Args:
            method: HTTP method ('GET' or 'POST')
            url: Request URL
            json_data: JSON payload for POST requests
            username: Username for authentication (if needed)
            password: Password for authentication (if needed)
            sync_id: Sync ID for authentication (if needed)
            
        Returns:
            requests.Response: The HTTP response object
            
        Raises:
            APINetworkError: For network-related errors
            APICallError: For other API-related errors
        """
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            # Get valid auth token
            auth_token = self.token_manager.get_valid_auth_token()
            if not auth_token:
                raise APIAuthenticationError("No valid authentication token available")
            
            # Prepare headers with Token authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Make request
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=json_data, headers=headers, timeout=10)
            else:
                raise APICallError(f"Unsupported HTTP method: {method}")
            
            # Handle token expiration/invalidation
            if response.status_code == 401 and username and password and sync_id:
                self.logger.warning("Authentication token invalid, attempting re-login")
                # Clear invalid token
                self.token_manager.clear_tokens()
                # Get new token
                new_token = self.get_valid_auth_token(url, username, password, sync_id)
                if new_token:
                    # Retry request with new token
                    headers["Authorization"] = f"Token {new_token}"
                    
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