#!/usr/bin/env python3
"""
Gmail OAuth Handler - handles the complete OAuth flow with local server
Based on the reference implementation
"""

import os
import json
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

def authenticate_gmail(client_id: str, client_secret: str, token_file: str = None) -> dict:
    """
    Authenticate with Gmail using OAuth2 with a local server to catch the callback.
    
    Args:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        token_file: Optional path to save/load token
        
    Returns:
        dict with success status and credentials or error
    """
    try:
        creds = None
        token_path = token_file or os.path.expanduser("~/.mirix/gmail_token.json")
        
        # Load existing token if available
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception:
                pass
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            
            if not creds:
                # Create the client config
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [
                            "http://localhost:8080/",
                            "http://localhost:8081/",
                            "http://localhost:8082/"
                        ]
                    }
                }
                
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                
                # Try specific ports that match redirect URIs (exactly like reference)
                for port in [8080, 8081, 8082]:
                    try:
                        # This will open the browser and run a local server to catch the callback
                        # Set open_browser=True to match reference implementation
                        creds = flow.run_local_server(port=port, open_browser=True)
                        break
                    except OSError:
                        if port == 8082:
                            # If all ports fail, use automatic port selection
                            creds = flow.run_local_server(port=0, open_browser=True)
            
            # Save the credentials for the next run
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        return {
            "success": True,
            "message": "Gmail authenticated successfully",
            "token_path": token_path
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_auth_url(client_id: str, client_secret: str) -> dict:
    """
    Get the OAuth authorization URL without starting a local server.
    This is used when we want to handle the OAuth flow manually.
    """
    try:
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [
                    "http://localhost:8080/",
                    "http://localhost:8081/",
                    "http://localhost:8082/"
                ]
            }
        }
        
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        flow.redirect_uri = "http://localhost:8080/"
        
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline'
        )
        
        return {
            "success": True,
            "auth_url": auth_url,
            "flow": flow  # Return flow object for later use
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }