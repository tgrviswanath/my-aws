# Steps — Project 10.2 Disaster Recovery Architecture

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="db_password=Admin@1234!" \
  -var="primary_vpc_id=vpc-xxxxxxxxxx" \
  -var='primary_subnet_ids=["subnet-xxx","subnet-yyy"]' \
  -var="dr_vpc_id=vpc-yyyyyyyyyy" \
  -var='dr_subnet_ids=["subnet-aaa","subnet-bbb"]'
```

---

## Phase 2 — Verify S3 Replication

```bash
PRIMARY_BUCKET=$(terraform output -raw primary_s3_bucket)
DR_BUCKET=$(terraform output -raw dr_s3_bucket)

# Upload file to primary
echo "test data" | aws s3 cp - s3://$PRIMARY_BUCKET/test.txt --region us-east-1

# Wait ~15 minutes for replication
sleep 60

# Check DR bucket
aws s3 ls s3://$DR_BUCKET/ --region us-west-2
# Should see test.txt replicated
```

---

## Phase 3 — Verify RDS Replication Lag

```bash
# Check replication lag on DR replica
aws rds describe-db-instances \
  --db-instance-identifier handson-dr-replica \
  --region us-west-2 \
  --query "DBInstances[0].StatusInfos"
# Look for: ReplicaLag in seconds
```

---

## Phase 4 — Simulate Failover (DR Test)

```bash
# Step 1: Promote RDS read replica to standalone primary
aws rds promote-read-replica \
  --db-instance-identifier handson-dr-replica \
  --region us-west-2

# Wait for promotion (~5 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier handson-dr-replica \
  --region us-west-2

# Step 2: Update Route53 to point to DR region
# (manually or via health check failover)

# Step 3: Scale up ECS in DR region
aws ecs update-service \
  --cluster handson-dr-cluster \
  --service handson-flask-api-service \
  --desired-count 2 \
  --region us-west-2

echo "Failover complete — traffic now in us-west-2"
```

---

## Phase 5 — Measure RTO and RPO

```bash
# Record failover start time
START=$(date +%s)

# ... perform failover steps ...

# Record when service is restored
END=$(date +%s)
RTO=$((END - START))
echo "RTO: $RTO seconds ($(($RTO/60)) minutes)"

# RPO = time of last successful replication before failure
# Check S3 replication timestamp and RDS replica lag
```

---

## Screenshots to Take
- [ ] S3 replication configuration active
- [ ] File replicated to DR bucket
- [ ] RDS read replica in DR region
- [ ] Replication lag metric (should be < 60s)
- [ ] RDS promotion to standalone primary
- [ ] Route53 failover routing switching to DR
