-- CloudTrail Log Analytics Queries
-- Run in Athena after creating the cloudtrail table (see terraform/main.tf)

-- ─── 1. Top 10 API callers in the last 7 days ────────────────────────────────
SELECT
    useridentity.arn AS caller,
    COUNT(*) AS api_call_count
FROM cloudtrail_logs
WHERE year = '2024'
  AND month = '01'
  AND eventtime >= DATE_FORMAT(CURRENT_DATE - INTERVAL '7' DAY, '%Y-%m-%dT%H:%i:%sZ')
GROUP BY useridentity.arn
ORDER BY api_call_count DESC
LIMIT 10;

-- ─── 2. Failed API calls (AccessDenied errors) ───────────────────────────────
SELECT
    eventtime,
    useridentity.arn AS caller,
    eventsource,
    eventname,
    errormessage
FROM cloudtrail_logs
WHERE year = '2024'
  AND errorcode IN ('AccessDenied', 'UnauthorizedOperation')
ORDER BY eventtime DESC
LIMIT 50;

-- ─── 3. Root account usage (security alert) ──────────────────────────────────
SELECT
    eventtime,
    eventname,
    eventsource,
    sourceipaddress
FROM cloudtrail_logs
WHERE year = '2024'
  AND useridentity.type = 'Root'
ORDER BY eventtime DESC;

-- ─── 4. IAM changes (user/role/policy modifications) ─────────────────────────
SELECT
    eventtime,
    useridentity.arn AS who_made_change,
    eventname,
    requestparameters
FROM cloudtrail_logs
WHERE year = '2024'
  AND eventsource = 'iam.amazonaws.com'
  AND eventname IN ('CreateUser', 'DeleteUser', 'AttachRolePolicy',
                    'DetachRolePolicy', 'CreateRole', 'DeleteRole',
                    'PutUserPolicy', 'CreateAccessKey')
ORDER BY eventtime DESC;

-- ─── 5. S3 bucket deletions ───────────────────────────────────────────────────
SELECT
    eventtime,
    useridentity.arn AS who,
    requestparameters
FROM cloudtrail_logs
WHERE year = '2024'
  AND eventsource = 's3.amazonaws.com'
  AND eventname IN ('DeleteBucket', 'DeleteObject', 'DeleteObjects')
ORDER BY eventtime DESC;

-- ─── 6. API calls by region ───────────────────────────────────────────────────
SELECT
    awsregion,
    COUNT(*) AS call_count
FROM cloudtrail_logs
WHERE year = '2024'
GROUP BY awsregion
ORDER BY call_count DESC;
