"""
log_shipper.py — Ship application logs to CloudWatch Logs.

Usage:
    # Send a single log message
    python log_shipper.py --log-group /app/myservice --message "test log"

    # Tail a log file and ship new lines continuously
    python log_shipper.py --log-group /app/myservice --file app.log

What this script does:
    1. Creates the log group and log stream if they don't exist
    2. Sends a single log message (--message mode)
    3. Tails a log file and ships new lines to CloudWatch (--file mode)
    4. Handles sequence tokens correctly (required by CloudWatch PutLogEvents API)
    5. Prints the CloudWatch Logs console URL for the stream

Prerequisites:
    pip install boto3
    AWS credentials configured (aws configure or IAM role)
"""

import argparse
import os
import time
import datetime
import boto3
from botocore.exceptions import ClientError


# ── AWS client ────────────────────────────────────────────────────────────────
logs = boto3.client("logs")


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_log_group(log_group_name: str, retention_days: int = 30) -> None:
    """
    Create the log group if it doesn't already exist, and set retention.

    Args:
        log_group_name: CloudWatch log group name (e.g. '/app/myservice')
        retention_days: Log retention in days (default: 30)
    """
    try:
        logs.create_log_group(logGroupName=log_group_name)
        print(f"  ✓ Created log group: {log_group_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print(f"  ℹ Log group already exists: {log_group_name}")
        else:
            raise

    # Always (re)apply retention policy to ensure it's set correctly
    logs.put_retention_policy(
        logGroupName=log_group_name,
        retentionInDays=retention_days,
    )


def ensure_log_stream(log_group_name: str, log_stream_name: str) -> None:
    """
    Create the log stream inside the log group if it doesn't already exist.

    Args:
        log_group_name:  Parent log group name
        log_stream_name: Log stream name (e.g. 'app-instance-1')
    """
    try:
        logs.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
        )
        print(f"  ✓ Created log stream: {log_stream_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print(f"  ℹ Log stream already exists: {log_stream_name}")
        else:
            raise


def get_sequence_token(log_group_name: str, log_stream_name: str) -> str | None:
    """
    Retrieve the current sequence token for a log stream.

    CloudWatch requires a sequence token for all PutLogEvents calls after the
    first one. The token is returned by the previous PutLogEvents call, or can
    be fetched from DescribeLogStreams.

    Args:
        log_group_name:  Log group name
        log_stream_name: Log stream name

    Returns:
        The sequence token string, or None if the stream has no events yet.
    """
    response = logs.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name,
    )
    for stream in response.get("logStreams", []):
        if stream["logStreamName"] == log_stream_name:
            return stream.get("uploadSequenceToken")  # None if stream is empty
    return None


def put_log_events(
    log_group_name: str,
    log_stream_name: str,
    messages: list[str],
    sequence_token: str | None = None,
) -> str | None:
    """
    Send a batch of log messages to CloudWatch Logs.

    Args:
        log_group_name:  Target log group
        log_stream_name: Target log stream
        messages:        List of log message strings to send
        sequence_token:  Current sequence token (None for first batch)

    Returns:
        The next sequence token (use for subsequent calls)
    """
    # Build log events with millisecond timestamps
    now_ms = int(time.time() * 1000)
    log_events = [
        {"timestamp": now_ms + i, "message": msg}
        for i, msg in enumerate(messages)
    ]

    # Build kwargs — sequence token is only required after the first put
    kwargs = {
        "logGroupName": log_group_name,
        "logStreamName": log_stream_name,
        "logEvents": log_events,
    }
    if sequence_token:
        kwargs["sequenceToken"] = sequence_token

    try:
        response = logs.put_log_events(**kwargs)
        return response.get("nextSequenceToken")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        # InvalidSequenceTokenException includes the correct token in the message
        if error_code in ("InvalidSequenceTokenException", "DataAlreadyAcceptedException"):
            # Extract the expected token from the error message and retry once
            correct_token = e.response["Error"].get("expectedSequenceToken")
            print(f"  ⚠ Sequence token mismatch — retrying with correct token")
            kwargs["sequenceToken"] = correct_token
            response = logs.put_log_events(**kwargs)
            return response.get("nextSequenceToken")
        raise


def stream_url(log_group_name: str, log_stream_name: str) -> str:
    """
    Build the CloudWatch Logs console URL for a specific log stream.

    Args:
        log_group_name:  Log group name
        log_stream_name: Log stream name

    Returns:
        Console URL string
    """
    region = boto3.session.Session().region_name or "us-east-1"
    # URL-encode slashes in the group/stream names for the console link
    group_encoded = log_group_name.replace("/", "$252F")
    stream_encoded = log_stream_name.replace("/", "$252F")
    return (
        f"https://{region}.console.aws.amazon.com/cloudwatch/home"
        f"?region={region}#logsV2:log-groups/log-group/{group_encoded}"
        f"/log-events/{stream_encoded}"
    )


# ── Mode 1: Send a single message ─────────────────────────────────────────────

def send_single_message(log_group_name: str, log_stream_name: str, message: str) -> None:
    """
    Send a single log message to CloudWatch Logs.

    Args:
        log_group_name:  Target log group
        log_stream_name: Target log stream
        message:         The log message string
    """
    ensure_log_group(log_group_name)
    ensure_log_stream(log_group_name, log_stream_name)

    token = get_sequence_token(log_group_name, log_stream_name)
    put_log_events(log_group_name, log_stream_name, [message], token)

    print(f"\n  ✓ Message sent: {message}")
    print(f"  Stream URL: {stream_url(log_group_name, log_stream_name)}")


# ── Mode 2: Tail a log file ───────────────────────────────────────────────────

def tail_and_ship(
    log_group_name: str,
    log_stream_name: str,
    file_path: str,
    poll_interval: float = 1.0,
    batch_size: int = 100,
) -> None:
    """
    Continuously tail a log file and ship new lines to CloudWatch Logs.

    Reads from the current end of the file and ships any new lines that appear,
    similar to `tail -f`. Batches up to `batch_size` lines per API call.

    Press Ctrl+C to stop.

    Args:
        log_group_name:  Target log group
        log_stream_name: Target log stream
        file_path:       Path to the log file to tail
        poll_interval:   Seconds between file polls (default: 1.0)
        batch_size:      Max lines per PutLogEvents call (default: 100)
    """
    ensure_log_group(log_group_name)
    ensure_log_stream(log_group_name, log_stream_name)

    token = get_sequence_token(log_group_name, log_stream_name)

    print(f"\n  Tailing {file_path} → {log_group_name}/{log_stream_name}")
    print(f"  Press Ctrl+C to stop\n")

    with open(file_path, "r") as f:
        # Seek to end of file — only ship new lines written after this point
        f.seek(0, os.SEEK_END)

        try:
            while True:
                lines = []
                while len(lines) < batch_size:
                    line = f.readline()
                    if not line:
                        break  # No new data yet
                    lines.append(line.rstrip("\n"))

                if lines:
                    token = put_log_events(log_group_name, log_stream_name, lines, token)
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"  [{ts}] Shipped {len(lines)} line(s)")

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n  Stopped.")
            print(f"  Stream URL: {stream_url(log_group_name, log_stream_name)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ship application logs to CloudWatch Logs"
    )
    parser.add_argument(
        "--log-group", required=True,
        help="CloudWatch log group name (e.g. /app/myservice)"
    )
    parser.add_argument(
        "--log-stream", default=None,
        help="Log stream name (default: auto-generated from hostname + date)"
    )
    parser.add_argument(
        "--message", default=None,
        help="Single log message to send"
    )
    parser.add_argument(
        "--file", default=None,
        help="Log file to tail and ship continuously"
    )
    args = parser.parse_args()

    # Auto-generate a stream name if not provided
    if args.log_stream is None:
        date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        hostname = os.uname().nodename if hasattr(os, "uname") else "host"
        args.log_stream = f"{hostname}-{date_str}"

    print("\n=== CloudWatch Log Shipper ===\n")

    if args.message:
        send_single_message(args.log_group, args.log_stream, args.message)
    elif args.file:
        tail_and_ship(args.log_group, args.log_stream, args.file)
    else:
        parser.error("Provide either --message or --file")


if __name__ == "__main__":
    main()
