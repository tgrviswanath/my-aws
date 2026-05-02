"""
AWS Lambda — Serverless Order Management API
Triggers: API Gateway (HTTP), SQS (async processing), EventBridge (scheduled)
Uses: DynamoDB, SQS, SNS, Secrets Manager, X-Ray
"""

import json
import os
import time
import uuid
import logging
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder, patch_all

# Patch all supported libraries for X-Ray tracing
patch_all()

# ── Structured logging ────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log(level, message, **kwargs):
    entry = {
        "level": level,
        "message": message,
        "service": "order-api",
        **kwargs
    }
    getattr(logger, level.lower())(json.dumps(entry))

# ── AWS Clients (initialized outside handler for reuse) ───────────────────────
dynamodb = boto3.resource('dynamodb')
sqs      = boto3.client('sqs')
sns      = boto3.client('sns')

TABLE_NAME     = os.environ['ORDERS_TABLE']
QUEUE_URL      = os.environ['ORDER_QUEUE_URL']
SNS_TOPIC_ARN  = os.environ.get('NOTIFICATION_TOPIC_ARN', '')

table = dynamodb.Table(TABLE_NAME)

# ── Helper: JSON response ─────────────────────────────────────────────────────
def response(status_code: int, body: dict, headers: dict = None) -> dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-Id': xray_recorder.current_segment().trace_id if xray_recorder.current_segment() else '',
            **(headers or {})
        },
        'body': json.dumps(body, default=str)
    }

# ── Helper: Decimal serializer ────────────────────────────────────────────────
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# ── POST /orders — Create Order ───────────────────────────────────────────────
@xray_recorder.capture('create_order')
def create_order(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        customer_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')

        # Validate
        if not customer_id:
            return response(401, {'error': 'Unauthorized'})
        if not body.get('items') or not isinstance(body['items'], list):
            return response(400, {'error': 'items[] is required'})

        # Build order
        order_id = str(uuid.uuid4())
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        total = sum(Decimal(str(i['price'])) * i['quantity'] for i in body['items'])

        order = {
            'customerId': customer_id,
            'orderId': order_id,
            'items': body['items'],
            'total': total,
            'status': 'PENDING',
            'createdAt': now,
            'updatedAt': now,
            'version': 1
        }

        # Save to DynamoDB (conditional — prevent duplicate)
        table.put_item(
            Item=order,
            ConditionExpression='attribute_not_exists(orderId)'
        )

        # Queue for async processing
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({'orderId': order_id, 'customerId': customer_id}),
            MessageGroupId=customer_id,
            MessageDeduplicationId=order_id
        )

        log('info', 'Order created', orderId=order_id, customerId=customer_id, total=str(total))

        return response(201, {'orderId': order_id, 'status': 'PENDING', 'total': float(total)})

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response(409, {'error': 'Order already exists'})
        log('error', 'DynamoDB error', error=str(e))
        return response(500, {'error': 'Internal server error'})
    except Exception as e:
        log('error', 'Unexpected error', error=str(e))
        return response(500, {'error': 'Internal server error'})

# ── GET /orders/{orderId} — Get Order ────────────────────────────────────────
@xray_recorder.capture('get_order')
def get_order(event, context):
    order_id   = event['pathParameters']['orderId']
    customer_id = event.get('queryStringParameters', {}).get('customerId')

    if not customer_id:
        return response(400, {'error': 'customerId query param required'})

    try:
        result = table.get_item(
            Key={'customerId': customer_id, 'orderId': order_id},
            ConsistentRead=True
        )
        item = result.get('Item')
        if not item:
            return response(404, {'error': 'Order not found'})

        return response(200, json.loads(json.dumps(item, cls=DecimalEncoder)))

    except Exception as e:
        log('error', 'GetOrder error', error=str(e), orderId=order_id)
        return response(500, {'error': 'Internal server error'})

# ── GET /orders — List Orders ─────────────────────────────────────────────────
@xray_recorder.capture('list_orders')
def list_orders(event, context):
    params      = event.get('queryStringParameters') or {}
    customer_id = params.get('customerId')
    status      = params.get('status')
    limit       = int(params.get('limit', '20'))

    if not customer_id:
        return response(400, {'error': 'customerId query param required'})

    try:
        kwargs = {
            'KeyConditionExpression': Key('customerId').eq(customer_id),
            'ScanIndexForward': False,
            'Limit': min(limit, 100)
        }
        if status:
            kwargs['FilterExpression'] = Attr('status').eq(status)

        result = table.query(**kwargs)
        items  = json.loads(json.dumps(result['Items'], cls=DecimalEncoder))

        return response(200, {
            'orders': items,
            'count': len(items),
            'nextKey': result.get('LastEvaluatedKey')
        })

    except Exception as e:
        log('error', 'ListOrders error', error=str(e))
        return response(500, {'error': 'Internal server error'})

# ── SQS Trigger — Process Order ───────────────────────────────────────────────
@xray_recorder.capture('process_order')
def process_order(event, context):
    failed_ids = []

    for record in event['Records']:
        message_id = record['messageId']
        body = json.loads(record['body'])
        order_id    = body['orderId']
        customer_id = body['customerId']

        try:
            # Read order
            result = table.get_item(Key={'customerId': customer_id, 'orderId': order_id})
            order  = result.get('Item')

            if not order:
                log('error', 'Order not found in queue', orderId=order_id)
                continue  # Don't retry — order doesn't exist

            # Simulate: inventory check + payment
            _check_inventory(order['items'])
            _process_payment(float(order['total']), customer_id)

            # Update status
            table.update_item(
                Key={'customerId': customer_id, 'orderId': order_id},
                UpdateExpression='SET #s = :status, updatedAt = :ts, version = version + :inc',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': 'CONFIRMED',
                    ':ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    ':inc': 1,
                    ':expected': 'PENDING'
                },
                ConditionExpression='#s = :expected'
            )

            # Notify
            if SNS_TOPIC_ARN:
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Message=json.dumps({'orderId': order_id, 'customerId': customer_id, 'status': 'CONFIRMED'}),
                    Subject='Order Confirmed',
                    MessageAttributes={
                        'eventType': {'DataType': 'String', 'StringValue': 'OrderConfirmed'}
                    }
                )

            log('info', 'Order processed', orderId=order_id)

        except Exception as e:
            log('error', 'ProcessOrder failed', orderId=order_id, error=str(e))
            failed_ids.append({'itemIdentifier': message_id})

    # Report partial batch failures
    return {'batchItemFailures': failed_ids}

# ── EventBridge Scheduled — Daily Cleanup ────────────────────────────────────
@xray_recorder.capture('daily_cleanup')
def daily_cleanup(event, context):
    log('info', 'Daily cleanup started')
    cutoff = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - 90 * 86400))

    try:
        result = table.scan(
            FilterExpression=Attr('status').is_in(['DELIVERED', 'CANCELLED']) & Attr('updatedAt').lt(cutoff),
            ProjectionExpression='customerId, orderId'
        )

        deleted = 0
        with table.batch_writer() as batch:
            for item in result['Items']:
                batch.delete_item(Key={'customerId': item['customerId'], 'orderId': item['orderId']})
                deleted += 1

        log('info', 'Cleanup complete', deleted=deleted)
        return {'deleted': deleted}

    except Exception as e:
        log('error', 'Cleanup error', error=str(e))
        raise

# ── Main Handler (routes by event source) ────────────────────────────────────
def handler(event, context):
    # SQS trigger
    if 'Records' in event and event['Records'][0].get('eventSource') == 'aws:sqs':
        return process_order(event, context)

    # EventBridge / CloudWatch Events
    if 'source' in event or 'detail-type' in event:
        return daily_cleanup(event, context)

    # API Gateway
    http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', '')
    path        = event.get('path', '') or event.get('rawPath', '')

    if http_method == 'POST' and '/orders' in path:
        return create_order(event, context)
    elif http_method == 'GET' and '/orders/' in path:
        return get_order(event, context)
    elif http_method == 'GET' and path.endswith('/orders'):
        return list_orders(event, context)

    return response(404, {'error': 'Not found'})

# ── Helpers ───────────────────────────────────────────────────────────────────
def _check_inventory(items):
    """Stub: check inventory service"""
    time.sleep(0.05)

def _process_payment(amount: float, customer_id: str):
    """Stub: process payment"""
    time.sleep(0.1)
