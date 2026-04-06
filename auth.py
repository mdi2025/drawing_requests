#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Works with Python 3.4+ — no external libraries needed

import json
import time
import socket
import urllib.request
import urllib.parse
import urllib.error

from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT

# ---------------------------------------------------------------
# Retry settings
# ---------------------------------------------------------------
_MAX_RETRIES  = 3    # how many times to try before giving up
_RETRY_DELAY  = 2    # seconds to wait between retries


def _post(action_payload, timeout=None):
    """
    Internal helper — sends a POST request to the API.
    Returns the parsed JSON dict, or raises an exception.

    Handles:
      - Network errors / connection refused
      - Timeouts
      - PHP warnings prepended before JSON
      - Bad JSON responses
    """
    if timeout is None:
        timeout = API_TIMEOUT

    post_data = urllib.parse.urlencode(action_payload).encode("utf-8")

    req = urllib.request.Request(API_BASE_URL, data=post_data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Connection",   "keep-alive")

    response = urllib.request.urlopen(req, timeout=timeout)
    raw = response.read().decode("utf-8").strip()

    # Strip any PHP notices/warnings that appear before the JSON
    json_start = raw.find("{")
    if json_start == -1:
        raise ValueError("No JSON found in server response: " + repr(raw[:200]))

    return json.loads(raw[json_start:])


def _post_with_retry(action_payload):
    """
    Calls _post() with automatic retry on transient errors.
    Only retries on network/timeout errors — not on wrong password etc.
    """
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return _post(action_payload)

        except urllib.error.URLError as e:
            last_error = e
            reason = str(e.reason) if hasattr(e, "reason") else str(e)
            print("Attempt {}/{} failed (URLError): {}".format(attempt, _MAX_RETRIES, reason))

        except socket.timeout as e:
            last_error = e
            print("Attempt {}/{} failed (Timeout): request took longer than {}s".format(
                attempt, _MAX_RETRIES, API_TIMEOUT))

        except OSError as e:
            # Covers ConnectionResetError, BrokenPipeError etc.
            last_error = e
            print("Attempt {}/{} failed (OSError): {}".format(attempt, _MAX_RETRIES, e))

        except ValueError as e:
            # Bad/missing JSON — retrying usually won't help, but try once more
            last_error = e
            print("Attempt {}/{} failed (Bad response): {}".format(attempt, _MAX_RETRIES, e))

        if attempt < _MAX_RETRIES:
            print("Retrying in {}s...".format(_RETRY_DELAY))
            time.sleep(_RETRY_DELAY)

    raise last_error  # re-raise the last error after all retries exhausted


def authenticate(username, password):
    """
    Authenticate user via the Drawing Management System API.
    Sends a POST request with action=login.
    The API handles MD5 hashing server-side.

    Args:
        username : admin_name from drawing_users table
        password : plain text password

    Returns:
        tuple: (success, permissions, user_id)
            success     : True if login succeeded
            permissions : list of page IDs the user can access
            user_id     : int DB id of the user, or None on failure

    Page Permission IDs:
        1 = Drawing Requests
        2 = Drawing Issuance
        3 = Return
        4 = Reports
        5 = User Management
    """
    payload = {
        "action":   "login",
        "username": username,
        "password": password,
    }

    try:
        result = _post_with_retry(payload)

        if result.get("response") == "true":
            data          = result.get("data", {})
            access_tokens = data.get("access_tokens", [])
            user_id       = data.get("id", None)

            # Normalize access_tokens — API sometimes returns it as a JSON string
            if isinstance(access_tokens, str):
                try:
                    access_tokens = json.loads(access_tokens)
                except Exception:
                    access_tokens = []

            if not isinstance(access_tokens, list):
                access_tokens = []

            return (True, access_tokens, user_id)

        else:
            # Server responded but credentials were wrong — don't retry
            print("Login failed:", result.get("message", "Invalid username or password"))
            return (False, [], None)

    except Exception as e:
        print("Authentication error after {} attempts: {} — {}".format(
            _MAX_RETRIES, type(e).__name__, e))
        return (False, [], None)