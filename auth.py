#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

try:
    # Python 3
    import urllib.request as urllib_request
    import urllib.parse as urllib_parse
except ImportError:
    # Python 2 fallback
    import urllib as urllib_request
    import urllib as urllib_parse

from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT


def authenticate(username, password):
    """
    Authenticate user via the Drawing Management System API.

    Sends a POST request to the API with action=login.
    The API handles MD5 hashing server-side.

    Args:
        username: The admin_name from drawing_users table
        password: The plain text password to verify

    Returns:
        tuple: (success: bool, permissions: list, user_id: int|None)
            - success:     True if authentication successful
            - permissions: List of page IDs user has access to
            - user_id:     The user's DB id (or None on failure)

    Page Permission IDs:
        1 = Drawing Requests
        2 = Drawing Issuance
        3 = Return
        4 = Reports
        5 = User Management
    """
    try:
        # Build POST payload
        post_data = urllib_parse.urlencode(
            {
                "action": "login",
                "username": username,
                "password": password,
            }
        ).encode("utf-8")

        # Make the HTTP POST request
        req = urllib_request.Request(API_BASE_URL, data=post_data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        response = urllib_request.urlopen(req, timeout=API_TIMEOUT)
        raw = response.read().decode("utf-8")

        # Parse JSON response
        result = json.loads(raw)

        if result.get("response") == "true":
            data = result.get("data", {})
            access_tokens = data.get("access_tokens", [])
            user_id = data.get("id", None)

            # Ensure access_tokens is a list
            if isinstance(access_tokens, str):
                try:
                    access_tokens = json.loads(access_tokens)
                except Exception:
                    access_tokens = []
            if not isinstance(access_tokens, list):
                access_tokens = []

            return (True, access_tokens, user_id)
        else:
            return (False, [], None)

    except Exception as e:
        print("Authentication error: {}".format(e))
        return (False, [], None)
