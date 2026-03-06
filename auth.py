#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
from db_handler import db

def authenticate(username, password):
    """
    Authenticate user against drawing_users table.
    Password is compared using MD5 hash.
    
    Args:
        username: The admin_name from drawing_users table
        password: The plain text password to verify
        
    Returns:
        tuple: (success: bool, permissions: list)
            - success: True if authentication successful, False otherwise
            - permissions: List of page IDs user has access to (empty if auth failed)
            
    Page Permission IDs:
        1 = Drawing Requests
        2 = Drawing Issuance
        3 = Return
        4 = Reports
        5 = User Management
    """
    try:
        # Hash the provided password with MD5
        password_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
        
        # Query the drawing_users table (include access_tokens)
        query = """
            SELECT id, admin_name, access_tokens 
            FROM drawing_users 
            WHERE admin_name = %s AND admin_pass = %s
        """
        result = db.fetch_all(query, (username, password_md5))
        
        # If we get a result, authentication is successful
        if result and len(result) > 0:
            user = result[0]
            # Parse access_tokens (JSON field)
            import json
            access_tokens = user.get('access_tokens', [])
            
            # Handle if access_tokens is a string (JSON string)
            if isinstance(access_tokens, str):
                try:
                    access_tokens = json.loads(access_tokens)
                except:
                    access_tokens = []
            
            # Ensure it's a list
            if not isinstance(access_tokens, list):
                access_tokens = []
                
            return (True, access_tokens)
        return (False, [])
        
    except Exception as e:
        print("Authentication error: {}".format(e))
        return (False, [])
