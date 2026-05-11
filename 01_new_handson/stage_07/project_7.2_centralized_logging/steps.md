# Steps — Project 7.2 Centralized Logging Platform

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="master_password=Admin@1234!" \
  -auto-approve

KIBANA_URL=$(terraform output -raw kibana_url)
echo "Kibana: $KIBANA_URL"
# Takes ~15 minutes for OpenSearch to be available
```

---

## Phase 2 — Generate Logs

```bash
# Generate traffic to produce logs
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"
for i in {1..50}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/items  > /dev/null
  curl -s $ALB_URL/nonexistent > /dev/null  # generates 404 logs
done

# Wait 60-120 seconds for Firehose to buffer and deliver
sleep 120
```

---

## Phase 3 — Explore Kibana

```
1. Open: https://OPENSEARCH_ENDPOINT/_dashboards
2. Login: admin / Admin@1234!
3. Go to: Stack Management → Index Patterns
4. Create index pattern: ecs-logs-*
5. Time field: @timestamp
6. Go to: Discover
7. Search: filter by log level, path, status code
```

---

## Phase 4 — Create Kibana Visualizations

```
1. Visualize → Create visualization
2. Lens → Bar chart
   X-axis: @timestamp (auto interval)
   Y-axis: Count of records
   Split by: status_code keyword

3. Save as: "Request Count by Status Code"

4. Dashboard → Create → Add visualization
```

---

## Phase 5 — Query via OpenSearch API

```bash
ENDPOINT=$(terraform output -raw opensearch_endpoint)

# Search for errors
curl -u admin:Admin@1234! \
  "https://$ENDPOINT/ecs-logs-*/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": { "@message": "ERROR" }
    },
    "size": 10,
    "sort": [{ "@timestamp": "desc" }]
  }' | python3 -m json.tool
```

---

## Screenshots to Take
- [ ] OpenSearch domain in Available state
- [ ] Firehose delivery stream active
- [ ] CloudWatch subscription filter configured
- [ ] Kibana Discover showing log entries
- [ ] Kibana visualization (bar chart of requests)
- [ ] OpenSearch API query returning results
