#!/bin/bash
# =============================================================================
# deploy_website.sh — Deploy a static website to S3 + invalidate CloudFront
#
# Usage:
#   ./deploy_website.sh <bucket-name> <cloudfront-distribution-id> [source-dir]
#
# Arguments:
#   bucket-name              S3 bucket name (must already exist)
#   cloudfront-distribution-id  CloudFront distribution ID (e.g. E1ABCDEF123456)
#   source-dir               Local directory to deploy (default: ./site)
#
# Prerequisites:
#   - AWS CLI configured with appropriate permissions
#   - S3 bucket with static website hosting enabled
#   - CloudFront distribution pointing to the S3 bucket
#
# IAM Permissions Required:
#   s3:PutObject, s3:DeleteObject, s3:ListBucket
#   cloudfront:CreateInvalidation
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Validate arguments ─────────────────────────────────────────────────────────
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <bucket-name> <distribution-id> [source-dir]"
    echo ""
    echo "  bucket-name       S3 bucket name"
    echo "  distribution-id   CloudFront distribution ID (e.g. E1ABCDEF123456)"
    echo "  source-dir        Local directory to deploy (default: ./site)"
    exit 1
fi

BUCKET_NAME="$1"
DISTRIBUTION_ID="$2"
SOURCE_DIR="${3:-./site}"

# ── Validate source directory ──────────────────────────────────────────────────
if [[ ! -d "${SOURCE_DIR}" ]]; then
    error "Source directory '${SOURCE_DIR}' does not exist."
fi

# ── Validate AWS CLI is installed ──────────────────────────────────────────────
if ! command -v aws &>/dev/null; then
    error "AWS CLI is not installed. Install it from https://aws.amazon.com/cli/"
fi

# ── Print deployment plan ──────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Static Website Deployment"
echo "============================================================"
echo "  Source      : ${SOURCE_DIR}"
echo "  S3 Bucket   : s3://${BUCKET_NAME}"
echo "  CloudFront  : ${DISTRIBUTION_ID}"
echo "============================================================"
echo ""

# =============================================================================
# STEP 1 — Sync files to S3
# =============================================================================
info "Step 1: Syncing files to S3..."

# --delete removes files in S3 that no longer exist locally
# --cache-control sets browser caching headers
# We sync HTML/CSS/JS with short cache, assets with long cache

# Short-lived cache for HTML files (always fresh)
aws s3 sync "${SOURCE_DIR}" "s3://${BUCKET_NAME}" \
    --delete \
    --exclude "*" \
    --include "*.html" \
    --cache-control "no-cache, no-store, must-revalidate" \
    --content-type "text/html; charset=utf-8"

# Medium cache for CSS and JS (1 hour)
aws s3 sync "${SOURCE_DIR}" "s3://${BUCKET_NAME}" \
    --exclude "*" \
    --include "*.css" \
    --include "*.js" \
    --cache-control "public, max-age=3600"

# Long cache for images and fonts (1 year — use content hashing in filenames)
aws s3 sync "${SOURCE_DIR}" "s3://${BUCKET_NAME}" \
    --exclude "*" \
    --include "*.png" \
    --include "*.jpg" \
    --include "*.jpeg" \
    --include "*.gif" \
    --include "*.svg" \
    --include "*.ico" \
    --include "*.woff" \
    --include "*.woff2" \
    --cache-control "public, max-age=31536000, immutable"

# Sync everything else (no specific cache header)
aws s3 sync "${SOURCE_DIR}" "s3://${BUCKET_NAME}" \
    --exclude "*.html" \
    --exclude "*.css" \
    --exclude "*.js" \
    --exclude "*.png" \
    --exclude "*.jpg" \
    --exclude "*.jpeg" \
    --exclude "*.gif" \
    --exclude "*.svg" \
    --exclude "*.ico" \
    --exclude "*.woff" \
    --exclude "*.woff2"

success "Files synced to s3://${BUCKET_NAME}"

# =============================================================================
# STEP 2 — Set bucket policy for public read (static website hosting)
# =============================================================================
info "Step 2: Verifying S3 bucket website configuration..."

# Check if website hosting is enabled
WEBSITE_CONFIG=$(aws s3api get-bucket-website --bucket "${BUCKET_NAME}" 2>&1 || true)
if echo "${WEBSITE_CONFIG}" | grep -q "NoSuchWebsiteConfiguration"; then
    warn "Static website hosting is not enabled on this bucket."
    warn "Enable it with:"
    warn "  aws s3 website s3://${BUCKET_NAME} --index-document index.html --error-document error.html"
else
    success "Static website hosting is configured."
fi

# =============================================================================
# STEP 3 — Invalidate CloudFront cache
# =============================================================================
info "Step 3: Creating CloudFront cache invalidation..."

# Invalidate all paths — use specific paths in production to save costs
# Each invalidation path after the first 1000/month costs $0.005
INVALIDATION_OUTPUT=$(aws cloudfront create-invalidation \
    --distribution-id "${DISTRIBUTION_ID}" \
    --paths "/*" \
    --output json)

INVALIDATION_ID=$(echo "${INVALIDATION_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Invalidation']['Id'])")
INVALIDATION_STATUS=$(echo "${INVALIDATION_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Invalidation']['Status'])")

success "CloudFront invalidation created: ${INVALIDATION_ID} (status: ${INVALIDATION_STATUS})"

# =============================================================================
# STEP 4 — Wait for invalidation to complete (optional)
# =============================================================================
info "Step 4: Waiting for CloudFront invalidation to complete..."
info "(This typically takes 30–60 seconds)"

aws cloudfront wait invalidation-completed \
    --distribution-id "${DISTRIBUTION_ID}" \
    --id "${INVALIDATION_ID}"

success "CloudFront cache invalidation complete."

# =============================================================================
# STEP 5 — Print deployment summary
# =============================================================================
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
    --id "${DISTRIBUTION_ID}" \
    --query "Distribution.DomainName" \
    --output text)

echo ""
echo "============================================================"
echo "  Deployment Complete"
echo "============================================================"
echo "  S3 Bucket URL  : http://${BUCKET_NAME}.s3-website-us-east-1.amazonaws.com"
echo "  CloudFront URL : https://${CLOUDFRONT_DOMAIN}"
echo "  Invalidation   : ${INVALIDATION_ID} — completed"
echo "============================================================"
echo ""
