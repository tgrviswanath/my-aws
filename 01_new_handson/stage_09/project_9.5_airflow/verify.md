# Verification & Validation — Project 9.5 Airflow Data Orchestration

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| MWAA Environment | MWAA → Environments | `handson-airflow` Status = **Available** |
| Airflow UI | MWAA → Environment → Open Airflow UI | Airflow login page loads |
| DAG in UI | Airflow UI → DAGs | `orders_pipeline` DAG listed, not paused |
| S3 DAGs Bucket | S3 → `handson-mwaa-*` → dags/ | DAG files uploaded |
| S3 Requirements | S3 → MWAA bucket → requirements.txt | requirements.txt present |
| VPC | MWAA → Environment → Networking | Private subnets configured |

📸 Screenshot: MWAA environment Status = Available  
📸 Screenshot: Airflow UI showing orders_pipeline DAG  
📸 Screenshot: DAG run history showing Succeeded runs  
📸 Screenshot: Task instance logs for a completed run

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm MWAA environment is available
aws mwaa get-environment \
  --name handson-airflow \
  --query "Environment.{Status:Status,AirflowVersion:AirflowVersion,WebserverUrl:WebserverUrl}"
# Expected: Status=AVAILABLE

# 2.2 Get Airflow UI URL
AIRFLOW_URL=$(aws mwaa get-environment \
  --name handson-airflow \
  --query "Environment.WebserverUrl" --output text)
echo "Airflow UI: https://$AIRFLOW_URL"

# 2.3 Confirm DAG files in S3
MWAA_BUCKET=$(aws mwaa get-environment \
  --name handson-airflow \
  --query "Environment.DagS3Path" --output text | cut -d'/' -f1)
aws s3 ls s3://$MWAA_BUCKET/dags/ --recursive
# Expected: orders_pipeline.py (or daily_pipeline.py) listed

# 2.4 Trigger DAG via CLI (using MWAA CLI token)
CLI_TOKEN=$(aws mwaa create-cli-token \
  --name handson-airflow \
  --query "CliToken" --output text)
WEBSERVER_HOSTNAME=$(aws mwaa get-environment \
  --name handson-airflow \
  --query "Environment.WebserverUrl" --output text)

# Trigger DAG
curl -s -X POST \
  "https://$WEBSERVER_HOSTNAME/aws_mwaa/cli" \
  -H "Authorization: Bearer $CLI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "dags trigger orders_pipeline"}' | python3 -m json.tool
# Expected: {"stdout": "Created <DagRun orders_pipeline ...>"}

# 2.5 List DAG runs
curl -s \
  "https://$WEBSERVER_HOSTNAME/aws_mwaa/cli" \
  -H "Authorization: Bearer $CLI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "dags list-runs -d orders_pipeline --limit 3"}' | python3 -m json.tool
# Expected: recent DAG runs listed with state

# 2.6 Check MWAA environment metrics
aws cloudwatch get-metric-statistics \
  --namespace AmazonMWAA \
  --metric-name RunningTasks \
  --dimensions Name=Function,Value=Scheduler Name=Environment,Value=handson-airflow \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average \
  --query "Datapoints[*].Average"
# Expected: metric data returned
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_mwaa_environment.main
# aws_s3_bucket.mwaa
# aws_s3_object.dag
# aws_s3_object.requirements
# aws_iam_role.mwaa
# aws_security_group.mwaa
# aws_vpc.main (or data source)

terraform state show aws_mwaa_environment.main
# Shows: name, airflow_version, environment_class, dag_s3_path

terraform output airflow_url
# Expected: https://xxx.c2.us-east-1.airflow.amazonaws.com

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — DAG Run Verification

```bash
CLI_TOKEN=$(aws mwaa create-cli-token \
  --name handson-airflow \
  --query "CliToken" --output text)
WEBSERVER_HOSTNAME=$(aws mwaa get-environment \
  --name handson-airflow \
  --query "Environment.WebserverUrl" --output text)

# Check DAG is loaded (not in error state)
curl -s \
  "https://$WEBSERVER_HOSTNAME/aws_mwaa/cli" \
  -H "Authorization: Bearer $CLI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "dags list"}' | python3 -c "
import sys, json, base64
resp = json.load(sys.stdin)
output = base64.b64decode(resp.get('stdout','')).decode()
print(output)
"
# Expected: orders_pipeline listed, is_paused=False

# Trigger and wait for completion
curl -s \
  "https://$WEBSERVER_HOSTNAME/aws_mwaa/cli" \
  -H "Authorization: Bearer $CLI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "dags trigger orders_pipeline"}' > /dev/null

echo "DAG triggered — check Airflow UI for run status"
echo "URL: https://$WEBSERVER_HOSTNAME"
```

---

## 5. Expected Successful Outputs

**CLI — get-environment:**
```json
{ "Status": "AVAILABLE", "AirflowVersion": "2.8.1", "WebserverUrl": "xxx.c2.us-east-1.airflow.amazonaws.com" }
```

**DAG trigger response:**
```json
{ "stdout": "Q3JlYXRlZCA8RGFnUnVuIG9yZGVyc19waXBlbGluZSBAMjAyNC0wMS0wMVQwMDowMDowMCswMDowMD4=" }
```
(base64 decoded: `Created <DagRun orders_pipeline @2024-01-01T00:00:00+00:00>`)

**DAG list output:**
```
dag_id          | filepath                | owner   | paused
orders_pipeline | /usr/local/airflow/dags | airflow | False
```

---

## 6. Verification Checklist

- [ ] MWAA environment `handson-airflow` Status = AVAILABLE
- [ ] Airflow UI URL accessible (login page loads)
- [ ] DAG files uploaded to S3 dags/ prefix
- [ ] `orders_pipeline` DAG visible in Airflow UI, not paused
- [ ] DAG trigger via CLI succeeds (DagRun created)
- [ ] DAG run completes with state = success
- [ ] Task instance logs accessible in Airflow UI
- [ ] MWAA CloudWatch metrics returning data
- [ ] `terraform plan` shows no changes
