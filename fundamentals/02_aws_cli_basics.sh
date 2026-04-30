#!/bin/bash
# AWS CLI Basics — Essential Commands Reference

# ── Authentication ─────────────────────────────────────────────────────────────
aws configure
aws configure --profile dev
aws sts get-caller-identity
aws sts assume-role \
  --role-arn arn:aws:iam::123456789:role/MyRole \
  --role-session-name MySession

# ── EC2 ────────────────────────────────────────────────────────────────────────
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,Type:InstanceType}" \
  --output table

aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name my-key-pair \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678 \
  --count 1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=MyServer}]'

aws ec2 start-instances --instance-ids i-1234567890abcdef0
aws ec2 stop-instances --instance-ids i-1234567890abcdef0
aws ec2 terminate-instances --instance-ids i-1234567890abcdef0

# ── S3 ─────────────────────────────────────────────────────────────────────────
aws s3 ls
aws s3 ls s3://my-bucket
aws s3 mb s3://my-new-bucket --region us-east-1
aws s3 cp file.txt s3://my-bucket/
aws s3 cp s3://my-bucket/file.txt .
aws s3 sync ./local-dir s3://my-bucket/prefix/
aws s3 rm s3://my-bucket/file.txt
aws s3 rb s3://my-bucket --force

# ── IAM ────────────────────────────────────────────────────────────────────────
aws iam list-users --output table
aws iam list-roles --output table
aws iam create-user --user-name alice
aws iam attach-user-policy \
  --user-name alice \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# ── Lambda ─────────────────────────────────────────────────────────────────────
aws lambda list-functions --output table
aws lambda invoke \
  --function-name my-function \
  --payload '{"key":"value"}' \
  response.json
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip

# ── CloudFormation ─────────────────────────────────────────────────────────────
aws cloudformation create-stack \
  --stack-name my-stack \
  --template-body file://template.yaml \
  --parameters ParameterKey=Env,ParameterValue=prod \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-stacks --stack-name my-stack
aws cloudformation delete-stack --stack-name my-stack

echo "AWS CLI reference complete!"
