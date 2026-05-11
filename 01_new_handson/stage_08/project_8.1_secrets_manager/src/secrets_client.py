"""
secrets_client.py — Retrieve secrets from AWS Secrets Manager and SSM Parameter Store.
Use this pattern in Lambda and ECS applications.
"""

import json
import os
import boto3
from botocore.exceptions import ClientError
from functools import lru_cache

# ─── Secrets Manager ──────────────────────────────────────────────────────────

_sm_client = boto3.client("secretsmanager")


@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> dict:
    """
    Retrieve a secret from Secrets Manager.
    Cached per Lambda cold start — not re-fetched on every invocation.
    """
    try:
        response = _sm_client.get_secret_value(SecretId=secret_name)
        secret_string = response.get("SecretString")
        if secret_string:
            return json.loads(secret_string)
        # Binary secret
        return {"binary": response["SecretBinary"]}
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise ValueError(f"Secret not found: {secret_name}")
        elif error_code == "AccessDeniedException":
            raise PermissionError(f"Access denied to secret: {secret_name}")
        raise


def get_db_credentials(secret_name: str) -> dict:
    """Get database credentials from Secrets Manager."""
    secret = get_secret(secret_name)
    return {
        "host":     secret["host"],
        "port":     int(secret.get("port", 3306)),
        "database": secret["dbname"],
        "user":     secret["username"],
        "password": secret["password"],
    }


# ─── SSM Parameter Store ──────────────────────────────────────────────────────

_ssm_client = boto3.client("ssm")


@lru_cache(maxsize=None)
def get_parameter(name: str, decrypt: bool = True) -> str:
    """Retrieve a parameter from SSM Parameter Store."""
    try:
        response = _ssm_client.get_parameter(
            Name=name,
            WithDecryption=decrypt
        )
        return response["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            raise ValueError(f"Parameter not found: {name}")
        raise


def get_parameters_by_path(path: str, decrypt: bool = True) -> dict:
    """Get all parameters under a path prefix."""
    paginator = _ssm_client.get_paginator("get_parameters_by_path")
    params = {}

    for page in paginator.paginate(Path=path, WithDecryption=decrypt, Recursive=True):
        for param in page["Parameters"]:
            # Strip the path prefix to get just the key name
            key = param["Name"].replace(path, "").lstrip("/")
            params[key] = param["Value"]

    return params


# ─── Usage Examples ───────────────────────────────────────────────────────────

def example_lambda_handler(event, context):
    """Example: retrieve secrets at Lambda cold start."""

    # Get DB credentials from Secrets Manager
    db_creds = get_db_credentials("/handson/prod/db-credentials")

    # Get app config from SSM Parameter Store
    config = get_parameters_by_path("/handson/prod/")
    # Returns: {"db_host": "...", "redis_host": "...", "feature_flag_x": "true"}

    # Get a single parameter
    api_key = get_parameter("/handson/prod/third-party-api-key")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Secrets retrieved successfully"})
    }
