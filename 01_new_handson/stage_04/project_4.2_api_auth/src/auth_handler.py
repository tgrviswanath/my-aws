"""
auth_handler.py — Handles user registration and login via Cognito.
"""

import json
import os
import boto3
from botocore.exceptions import ClientError

COGNITO_CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]
USER_POOL_ID      = os.environ["USER_POOL_ID"]

cognito = boto3.client("cognito-idp")


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def handler(event: dict, context) -> dict:
    path   = event.get("rawPath", "")
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    body   = json.loads(event.get("body") or "{}")

    try:
        if path == "/auth/register" and method == "POST":
            return register(body)
        elif path == "/auth/login" and method == "POST":
            return login(body)
        elif path == "/auth/refresh" and method == "POST":
            return refresh_token(body)
        else:
            return response(404, {"error": "Route not found"})
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON"})


def register(body: dict) -> dict:
    username = body.get("username")
    password = body.get("password")
    email    = body.get("email")

    if not all([username, password, email]):
        return response(400, {"error": "username, password, and email are required"})

    try:
        cognito.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        # Auto-confirm for development (remove in production)
        cognito.admin_confirm_sign_up(UserPoolId=USER_POOL_ID, Username=username)
        return response(201, {"message": f"User {username} registered successfully"})

    except cognito.exceptions.UsernameExistsException:
        return response(409, {"error": "Username already exists"})
    except cognito.exceptions.InvalidPasswordException as e:
        return response(400, {"error": str(e)})
    except ClientError as e:
        return response(500, {"error": str(e)})


def login(body: dict) -> dict:
    username = body.get("username")
    password = body.get("password")

    if not all([username, password]):
        return response(400, {"error": "username and password are required"})

    try:
        result = cognito.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        auth = result["AuthenticationResult"]
        return response(200, {
            "access_token":  auth["AccessToken"],
            "id_token":      auth["IdToken"],
            "refresh_token": auth["RefreshToken"],
            "expires_in":    auth["ExpiresIn"],
            "token_type":    auth["TokenType"],
        })

    except cognito.exceptions.NotAuthorizedException:
        return response(401, {"error": "Invalid username or password"})
    except cognito.exceptions.UserNotFoundException:
        return response(401, {"error": "Invalid username or password"})
    except ClientError as e:
        return response(500, {"error": str(e)})


def refresh_token(body: dict) -> dict:
    refresh = body.get("refresh_token")
    if not refresh:
        return response(400, {"error": "refresh_token is required"})

    try:
        result = cognito.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh},
        )
        auth = result["AuthenticationResult"]
        return response(200, {
            "access_token": auth["AccessToken"],
            "id_token":     auth["IdToken"],
            "expires_in":   auth["ExpiresIn"],
        })
    except ClientError as e:
        return response(401, {"error": "Invalid or expired refresh token"})
