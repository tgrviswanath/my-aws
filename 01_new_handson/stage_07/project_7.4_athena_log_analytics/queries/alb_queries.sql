-- ALB Access Log Analytics Queries

-- ─── 1. Request count by status code ─────────────────────────────────────────
SELECT
    elb_status_code,
    COUNT(*) AS request_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM alb_logs
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY elb_status_code
ORDER BY request_count DESC;

-- ─── 2. Top 10 slowest endpoints ─────────────────────────────────────────────
SELECT
    request_url,
    COUNT(*) AS request_count,
    ROUND(AVG(target_processing_time), 3) AS avg_latency_s,
    ROUND(APPROX_PERCENTILE(target_processing_time, 0.99), 3) AS p99_latency_s,
    MAX(target_processing_time) AS max_latency_s
FROM alb_logs
WHERE year = '2024' AND month = '01'
  AND target_processing_time > 0
GROUP BY request_url
ORDER BY p99_latency_s DESC
LIMIT 10;

-- ─── 3. Top source IPs ────────────────────────────────────────────────────────
SELECT
    client_ip,
    COUNT(*) AS request_count,
    SUM(received_bytes) AS total_bytes_received
FROM alb_logs
WHERE year = '2024' AND month = '01'
GROUP BY client_ip
ORDER BY request_count DESC
LIMIT 20;

-- ─── 4. Error rate over time ──────────────────────────────────────────────────
SELECT
    DATE_TRUNC('hour', PARSE_DATETIME(time, 'yyyy-MM-dd''T''HH:mm:ss.SSSSSS''Z')) AS hour,
    COUNT(*) AS total_requests,
    SUM(CASE WHEN elb_status_code >= 500 THEN 1 ELSE 0 END) AS error_5xx,
    ROUND(SUM(CASE WHEN elb_status_code >= 500 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS error_rate_pct
FROM alb_logs
WHERE year = '2024' AND month = '01'
GROUP BY 1
ORDER BY 1;

-- ─── 5. Requests by HTTP method ───────────────────────────────────────────────
SELECT
    request_verb AS method,
    COUNT(*) AS count
FROM alb_logs
WHERE year = '2024' AND month = '01'
GROUP BY request_verb
ORDER BY count DESC;
