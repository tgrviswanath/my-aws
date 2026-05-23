#!/usr/bin/env python3
"""
AWS CDK app — Three-tier VPC for Project 11.20
Deploy: cdk deploy
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct


class VpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
                 environment: str = "dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Three-tier VPC using CDK L2 construct
        self.vpc = ec2.Vpc(
            self, "VPC",
            vpc_name=f"vpc-{environment}-11-20-cdk",
            ip_addresses=ec2.IpAddresses.cidr("10.2.0.0/16"),
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="PrivateApp",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="PrivateDB",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # Tag all resources
        cdk.Tags.of(self).add("Environment", environment)
        cdk.Tags.of(self).add("ManagedBy", "cdk")
        cdk.Tags.of(self).add("Project", "11.20")

        # Outputs
        cdk.CfnOutput(self, "VpcId",
                      value=self.vpc.vpc_id,
                      description="VPC ID")
        cdk.CfnOutput(self, "PublicSubnets",
                      value=",".join([s.subnet_id for s in self.vpc.public_subnets]),
                      description="Public subnet IDs")
        cdk.CfnOutput(self, "PrivateAppSubnets",
                      value=",".join([s.subnet_id for s in self.vpc.private_subnets]),
                      description="Private app subnet IDs")
        cdk.CfnOutput(self, "IsolatedSubnets",
                      value=",".join([s.subnet_id for s in self.vpc.isolated_subnets]),
                      description="Isolated DB subnet IDs")


app = cdk.App()
env_name = app.node.try_get_context("environment") or "dev"

VpcStack(
    app, f"VpcStack-{env_name}-11-20",
    environment=env_name,
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
