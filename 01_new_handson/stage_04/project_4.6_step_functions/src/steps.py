"""
steps.py — Lambda handlers for each Step Functions state.
Each function receives the current state input and returns output
that gets merged into the state for the next step.
"""

import json
import os
import re
import time
import boto3

sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")


# ─── Step 1: Validate ─────────────────────────────────────────────────────────

def validate(event: dict, context) -> dict:
    """Validate the uploaded document."""
    print(f"Validating: {json.dumps(event)}")

    file_key  = event.get("file_key", "")
    file_size = event.get("file_size", 0)

    allowed_types = (".pdf", ".txt", ".docx", ".csv")
    if not any(file_key.lower().endswith(ext) for ext in allowed_types):
        raise ValueError(f"Unsupported file type: {file_key}")

    max_size_mb = 10
    if file_size > max_size_mb * 1024 * 1024:
        raise ValueError(f"File too large: {file_size} bytes (max {max_size_mb}MB)")

    return {
        **event,
        "validation": {
            "status": "passed",
            "file_type": file_key.rsplit(".", 1)[-1].lower(),
        }
    }


# ─── Step 2: Extract Text ─────────────────────────────────────────────────────

def extract_text(event: dict, context) -> dict:
    """Extract text content from the document."""
    print(f"Extracting text from: {event.get('file_key')}")

    # Simulate text extraction
    time.sleep(0.1)

    return {
        **event,
        "extraction": {
            "status": "completed",
            "word_count": 1250,
            "page_count": 3,
            "text_preview": "This document contains important information about...",
        }
    }


# ─── Step 3a: Classify (runs in parallel) ────────────────────────────────────

def classify(event: dict, context) -> dict:
    """Classify the document type."""
    print(f"Classifying document: {event.get('file_key')}")

    # Simulate ML classification
    categories = ["invoice", "contract", "report", "correspondence"]
    category = categories[hash(event.get("file_key", "")) % len(categories)]

    return {
        "classification": {
            "category":   category,
            "confidence": 0.92,
        }
    }


# ─── Step 3b: Check Compliance (runs in parallel) ────────────────────────────

def check_compliance(event: dict, context) -> dict:
    """Scan document for sensitive data (PII, etc.)."""
    print(f"Checking compliance for: {event.get('file_key')}")

    text = event.get("extraction", {}).get("text_preview", "")

    # Simple PII detection patterns
    has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
    has_ssn   = bool(re.search(r'\b\d{3}-\d{2}-\d{4}\b', text))

    return {
        "compliance": {
            "status":    "flagged" if (has_email or has_ssn) else "clean",
            "has_pii":   has_email or has_ssn,
            "has_email": has_email,
            "has_ssn":   has_ssn,
        }
    }


# ─── Step 4: Store Results ────────────────────────────────────────────────────

def store_results(event: dict, context) -> dict:
    """Store processing results to DynamoDB."""
    print(f"Storing results for: {event.get('file_key')}")

    # event contains merged results from parallel branches
    # In production: write to DynamoDB

    return {
        **event,
        "storage": {
            "status":     "saved",
            "record_id":  f"doc-{int(time.time())}",
        }
    }


# ─── Step 5: Notify ───────────────────────────────────────────────────────────

def notify(event: dict, context) -> dict:
    """Send completion notification."""
    print(f"Sending notification for: {event.get('file_key')}")

    message = {
        "file_key":      event.get("file_key"),
        "status":        "completed",
        "classification": event.get("classification", {}),
        "compliance":    event.get("compliance", {}),
        "record_id":     event.get("storage", {}).get("record_id"),
    }

    if SNS_TOPIC_ARN:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Document Processing Complete",
            Message=json.dumps(message, indent=2),
        )

    return {**event, "notification": {"status": "sent"}}
