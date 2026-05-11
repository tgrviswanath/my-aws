"""
protected_handler.py — Protected API endpoints.
API Gateway JWT Authorizer validates the token before this Lambda runs.
The decoded JWT claims are available in event["requestContext"]["authorizer"]["jwt"]["claims"].
"""

import json
import os


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def get_user_info(event: dict) -> dict:
    """Extract user info from JWT claims injected by API Gateway authorizer."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    return {
        "username": claims.get("cognito:username", claims.get("sub", "unknown")),
        "email":    claims.get("email", ""),
        "groups":   claims.get("cognito:groups", "").split(",") if claims.get("cognito:groups") else [],
    }


def is_admin(user_info: dict) -> bool:
    return "admin" in user_info.get("groups", [])


def handler(event: dict, context) -> dict:
    method   = event.get("requestContext", {}).get("http", {}).get("method", "")
    path     = event.get("rawPath", "")
    user     = get_user_info(event)

    # Admin-only operations
    if method in ("POST", "DELETE") and not is_admin(user):
        return response(403, {
            "error": "Forbidden",
            "message": f"User {user['username']} does not have admin privileges"
        })

    # Return user info for demonstration
    return response(200, {
        "message": f"Hello, {user['username']}!",
        "user":    user,
        "path":    path,
        "method":  method,
        "note":    "This endpoint is protected — you must have a valid JWT to reach here",
    })
