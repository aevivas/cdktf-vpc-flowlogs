#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformOutput
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.flow_log import FlowLog
from cdktf_cdktf_provider_aws.cloudwatch_log_group import CloudwatchLogGroup
from cdktf_cdktf_provider_aws.s3_bucket import S3Bucket
from cdktf_cdktf_provider_aws.s3_bucket_public_access_block import (
    S3BucketPublicAccessBlock,
)
from cdktf_cdktf_provider_aws.s3_bucket_versioning import S3BucketVersioningA
from cdktf_cdktf_provider_aws.s3_bucket_lifecycle_configuration import (
    S3BucketLifecycleConfiguration,
    S3BucketLifecycleConfigurationRule,
)
from cdktf_cdktf_provider_aws.iam_role import IamRole
from cdktf_cdktf_provider_aws.iam_role_policy import IamRolePolicy

import json
import settings

field_names = [
    "version",
    "account-id",
    "interface-id",
    "srcaddr",
    "dstaddr",
    "srcport",
    "dstport",
    "protocol",
    "packets",
    "bytes",
    "start",
    "end",
    "action",
    "log-status",
    "vpc-id",
    "subnet-id",
    "instance-id",
    "tcp-flags",
    "type",
    "pkt-srcaddr",
    "pkt-dstaddr",
    "region",
    "az-id",
    "sublocation-type",
    "sublocation-id",
    "pkt-src-aws-service",
    "pkt-dst-aws-service",
    "flow-direction",
    "traffic-path",
]

log_format = " ".join([f"$${{{n}}}" for n in field_names])


class VpcFlowLogsS3Stack(TerraformStack):
    """Creating VPC Flow logs with a bucket as a destination
    """

    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        AwsProvider(
            self,
            "AWS",
            region='us-east-1',
            default_tags=[{"tags": settings.tags}],
        )

        bucket_name = f"vpc-flow-logs-{settings.vpc_id}"

        bucket = S3Bucket(self, "bucket", bucket=bucket_name)

        S3BucketPublicAccessBlock(
            self,
            "public_access_block",
            bucket=bucket.id,
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
        )

        S3BucketVersioningA(
            self,
            "versioning",
            bucket=bucket.id,
            versioning_configuration={"status": "Disabled"},
        )

        rule = S3BucketLifecycleConfigurationRule(
            id="deleting-old-logs", status="Enabled", expiration={"days": 2}
        )

        S3BucketLifecycleConfiguration(self, "lifecycle", bucket=bucket.id, rule=[rule])

        TerraformOutput(self, "bucket_output", value=bucket.arn)

        flowlog_s3 = FlowLog(
            self,
            "flow-log-s3",
            vpc_id=settings.vpc_id,
            log_destination=bucket.arn,
            log_destination_type="s3",
            log_format=log_format,
            traffic_type="ALL",
            destination_options={
                "file_format": "plain-text",
                "per_hour_partition": True,
            },
            tags={"Name": "all-events-to-s3"},
        )

        TerraformOutput(self, "flowlog_s3_output", value=flowlog_s3.arn)


class VpcFlowLogsLogGroupStack(TerraformStack):
    """Creating VPC Flow logs with a Cloudwatch log group as a destination
    """
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        AwsProvider(
            self,
            "AWS",
            region='us-east-1',
            default_tags=[{"tags": settings.tags}],
        )

        log_group_name = f"/vpcflowlogs/{settings.vpc_id}"

        log_group = CloudwatchLogGroup(
            self, "log-group-log-group", name=log_group_name, retention_in_days=1
        )

        TerraformOutput(self, "log_group_output", value=log_group.arn)

        assume_role = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "vpc-flow-logs.amazonaws.com"},
                    "Effect": "Allow",
                }
            ],
        }
        iam_role_name = f"allow-vpc-flow-log-{settings.vpc_id}-to-log-group"

        iam_role = IamRole(
            self,
            "iam-role",
            name=iam_role_name,
            assume_role_policy=json.dumps(assume_role),
        )

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Resource": f"{log_group.arn}:*",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                    ],
                    "Effect": "Allow",
                }
            ],
        }

        IamRolePolicy(
            self,
            "iam-role-policy",
            name="default_policy",
            role=iam_role.id,
            policy=json.dumps(policy),
        )

        TerraformOutput(self, "iam_role_output", value=iam_role.arn)

        flowlog_loggroup = FlowLog(
            self,
            "flow-log-cloudwatch-log-group",
            vpc_id=settings.vpc_id,
            traffic_type="ALL",
            log_format=log_format,
            log_destination=log_group.arn,
            iam_role_arn=iam_role.arn,
            tags={"Name": "all-events-to-cloudwatch-log-groups"},
        )

        TerraformOutput(self, "flowlog_cloudwatch_output", value=flowlog_loggroup.arn)

app = App()

VpcFlowLogsS3Stack(app, "vpc-flowlogs-s3")
VpcFlowLogsLogGroupStack(app, "vpc-flowlogs-loggroup")

app.synth()


# https://github.com/ahmadalibagheri/cdktf-python-aws-iam
