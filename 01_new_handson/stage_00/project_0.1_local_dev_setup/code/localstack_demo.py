"""
localstack_demo.py — Test AWS services locally using LocalStack.

Prerequisites:
    docker-compose up -d   (starts LocalStack on port 4566)
    pip install boto3

Run:
    python localstack_demo.py

What this demo covers:
    - DynamoDB: create table, put items, scan
    - Lambda: create function from inline zip, invoke it
    - API Gateway: create REST API, resource, method, integration, deploy
"""

import boto3
import json
import zipfile
import io
import time

# ── LocalStack endpoint ────────────────────────────────────────────────────────
LOCALSTACK_URL = "http://localhost:4566"
AWS_REGION = "us-east-1"

# Dummy credentials — LocalStack accepts any non-empty values
BOTO3_KWARGS = dict(
    endpoint_url=LOCALSTACK_URL,
    region_name=AWS_REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)


# ── Helper: create boto3 client pointing at LocalStack ────────────────────────
def get_client(service: str):
    """Return a boto3 client configured to talk to LocalStack."""
    return boto3.client(service, **BOTO3_KWARGS)


def get_resource(service: str):
    """Return a boto3 resource configured to talk to LocalStack."""
    return boto3.resource(service, **BOTO3_KWARGS)


# ── 1. DynamoDB demo ──────────────────────────────────────────────────────────
def demo_dynamodb():
    """
    Create a DynamoDB table called 'local-items', insert 3 items, scan and print.
    """
    print("\n" + "=" * 60)
    print("  DynamoDB Demo")
    print("=" * 60)

    dynamodb = get_resource("dynamodb")
    table_name = "local-items"

    # Create table (idempotent — skip if already exists)
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "item_id", "KeyType": "HASH"},   # Partition key
            ],
            AttributeDefinitions=[
                {"AttributeName": "item_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        print(f"[+] Table '{table_name}' created.")
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        table = dynamodb.Table(table_name)
        print(f"[~] Table '{table_name}' already exists — reusing.")

    # Insert 3 sample items
    sample_items = [
        {"item_id": "001", "name": "Widget A", "price": 9.99,  "stock": 100},
        {"item_id": "002", "name": "Widget B", "price": 19.99, "stock": 50},
        {"item_id": "003", "name": "Widget C", "price": 4.99,  "stock": 200},
    ]

    for item in sample_items:
        table.put_item(Item=item)
        print(f"[+] Inserted item: {item['item_id']} — {item['name']}")

    # Scan and print all items
    response = table.scan()
    print(f"\n[*] Scan results ({response['Count']} items):")
    for item in response["Items"]:
        print(f"    {item}")

    return table_name


# ── 2. Lambda demo ────────────────────────────────────────────────────────────
def _build_lambda_zip() -> bytes:
    """
    Build an in-memory ZIP containing a minimal Lambda handler.
    Returns the raw ZIP bytes.
    """
    handler_code = b"""
def handler(event, context):
    return {
        "statusCode": 200,
        "body": {"hello": "from LocalStack", "event": event}
    }
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handler.py", handler_code)
    return buffer.getvalue()


def demo_lambda():
    """
    Create a Lambda function from an inline ZIP, invoke it, and print the response.
    """
    print("\n" + "=" * 60)
    print("  Lambda Demo")
    print("=" * 60)

    lambda_client = get_client("lambda")
    iam_client = get_client("iam")
    function_name = "local-hello-fn"

    # LocalStack needs a role ARN — any ARN works locally
    role_arn = "arn:aws:iam::000000000000:role/lambda-role"

    # Try to create the role (LocalStack may or may not enforce this)
    try:
        iam_client.create_role(
            RoleName="lambda-role",
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }],
            }),
        )
        print("[+] IAM role 'lambda-role' created.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("[~] IAM role already exists — reusing.")

    zip_bytes = _build_lambda_zip()

    # Create or update the function
    try:
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.11",
            Role=role_arn,
            Handler="handler.handler",
            Code={"ZipFile": zip_bytes},
            Description="LocalStack demo Lambda",
            Timeout=10,
        )
        print(f"[+] Lambda function '{function_name}' created.")
    except lambda_client.exceptions.ResourceConflictException:
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_bytes,
        )
        print(f"[~] Lambda function '{function_name}' updated.")

    # Wait briefly for LocalStack to register the function
    time.sleep(1)

    # Invoke the function
    payload = {"source": "localstack_demo", "version": "1.0"}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    result = json.loads(response["Payload"].read())
    print(f"[+] Lambda invocation result:")
    print(f"    Status code : {response['StatusCode']}")
    print(f"    Response    : {json.dumps(result, indent=6)}")

    return function_name


# ── 3. API Gateway demo ───────────────────────────────────────────────────────
def demo_api_gateway(lambda_function_name: str):
    """
    Create a REST API in API Gateway, wire it to the Lambda, deploy it,
    and print the local invocation URL.
    """
    print("\n" + "=" * 60)
    print("  API Gateway Demo")
    print("=" * 60)

    apigw = get_client("apigateway")
    api_name = "local-demo-api"

    # Create REST API
    api = apigw.create_rest_api(name=api_name, description="LocalStack demo API")
    api_id = api["id"]
    print(f"[+] REST API created: id={api_id}")

    # Get the root resource '/'
    resources = apigw.get_resources(restApiId=api_id)
    root_id = next(r["id"] for r in resources["items"] if r["path"] == "/")

    # Create /hello resource
    resource = apigw.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart="hello",
    )
    resource_id = resource["id"]
    print(f"[+] Resource '/hello' created: id={resource_id}")

    # Add GET method (no auth for demo)
    apigw.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="GET",
        authorizationType="NONE",
    )

    # Wire GET /hello → Lambda (AWS_PROXY integration)
    lambda_arn = (
        f"arn:aws:lambda:{AWS_REGION}:000000000000:function:{lambda_function_name}"
    )
    apigw.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="GET",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=(
            f"arn:aws:apigateway:{AWS_REGION}:lambda:path"
            f"/2015-03-31/functions/{lambda_arn}/invocations"
        ),
    )
    print(f"[+] Lambda integration configured.")

    # Deploy to 'dev' stage
    apigw.create_deployment(restApiId=api_id, stageName="dev")
    invoke_url = f"{LOCALSTACK_URL}/restapis/{api_id}/dev/_user_request_/hello"
    print(f"[+] API deployed to 'dev' stage.")
    print(f"[+] Invoke URL: {invoke_url}")
    print(f"    Test with:  curl {invoke_url}")

    return invoke_url


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("  LocalStack Demo — AWS Services Running Locally")
    print("=" * 60)
    print(f"  Endpoint : {LOCALSTACK_URL}")
    print(f"  Region   : {AWS_REGION}")

    results = {}

    # Run each demo
    results["dynamodb_table"] = demo_dynamodb()
    results["lambda_function"] = demo_lambda()
    results["api_gateway_url"] = demo_api_gateway(results["lambda_function"])

    # Summary
    print("\n" + "=" * 60)
    print("  Summary — What Was Tested Locally")
    print("=" * 60)
    print(f"  ✓ DynamoDB  : table '{results['dynamodb_table']}' created & populated")
    print(f"  ✓ Lambda    : function '{results['lambda_function']}' created & invoked")
    print(f"  ✓ API GW    : endpoint available at {results['api_gateway_url']}")
    print("\n  All AWS interactions ran against LocalStack — zero cloud cost.\n")


if __name__ == "__main__":
    main()
