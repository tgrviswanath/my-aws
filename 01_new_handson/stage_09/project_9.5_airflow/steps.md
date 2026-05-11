# Steps — Project 9.5 Airflow Data Orchestration

## Phase 1 — Run Airflow Locally (Free — Start Here)

```bash
# Run Airflow with Docker Compose
mkdir airflow-local && cd airflow-local

curl -LfO 'https://airflow.apache.org/docs/apache-airflow/stable/docker-compose.yaml'

# Initialize
mkdir -p ./dags ./logs ./plugins
echo "AIRFLOW_UID=$(id -u)" > .env

docker compose up airflow-init
docker compose up -d

# Open: http://localhost:8080
# Username: airflow, Password: airflow
```

---

## Phase 2 — Upload DAG

```bash
# Copy DAG to local dags folder
cp dags/daily_pipeline.py ./dags/

# Airflow auto-detects new DAGs within 30 seconds
# Check: http://localhost:8080/dags/daily_data_pipeline
```

---

## Phase 3 — Test DAG

```bash
# Trigger DAG manually
docker exec -it airflow-airflow-scheduler-1 \
  airflow dags trigger daily_data_pipeline

# Check task status
docker exec -it airflow-airflow-scheduler-1 \
  airflow tasks states-for-dag-run daily_data_pipeline $(date +%Y-%m-%dT%H:%M:%S+00:00)
```

---

## Phase 4 — Deploy to MWAA (AWS Managed Airflow)

```bash
cd terraform
terraform init && terraform apply -auto-approve

MWAA_ENV=$(terraform output -raw mwaa_environment_name)
MWAA_BUCKET=$(terraform output -raw mwaa_bucket)

# Upload DAGs to S3
aws s3 cp dags/ s3://$MWAA_BUCKET/dags/ --recursive

# Get Airflow UI URL
aws mwaa get-environment \
  --name $MWAA_ENV \
  --query "Environment.WebserverUrl" --output text
```

---

## Phase 5 — Monitor Pipeline

```
1. Open Airflow UI
2. DAGs → daily_data_pipeline → Graph view
3. Trigger manually: Actions → Trigger DAG
4. Watch tasks execute in order
5. Click a task → View logs
6. Check XCom values passed between tasks
```

---

## Screenshots to Take
- [ ] Airflow UI showing DAG graph
- [ ] DAG running with tasks in progress
- [ ] Task logs showing Glue job output
- [ ] Successful pipeline run (all tasks green)
- [ ] Failed task with retry behavior
- [ ] DAG schedule showing next run time
