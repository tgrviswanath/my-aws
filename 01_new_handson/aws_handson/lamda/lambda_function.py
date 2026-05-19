import json
from datetime import datetime

def lambda_handler(event, context):
    """
    Simple Lambda web app that returns JSON

    Args:
        event: Dict containing HTTP request details
        context: Lambda runtime context

    Returns:
        Dict with statusCode, headers, and JSON body
    """
    # Extract query parameters
    query_params = event.get('queryStringParameters', {}) or {}
    name = query_params.get('name', 'World')

    # Build response
    response = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'message': f'Hello, {name}!',
            'timestamp': datetime.now().isoformat(),
            'service': 'AWS Lambda Web App'
        })
    }

    return response
