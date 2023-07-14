# Deploying VPC Flow Logs destined to S3 or Cloudwatch Log Group

Two stacks for creating two VPC Flow logs: one to send logs to an S3 bucket and another to send logs to a Cloudwatch log group.

## Requirements

Terraform >= v1.5.2

cdktf >= 0.17.0

## Deployment

```
cdktf init --template="python"
pipenv install cdktf-cdktf-provider-aws
```

## Authorization

`export AWS_PROFILE="your_aws_profile"`

## Application Configuration

Configure `settings.py` with the VPC id where the Vpc Flow Log(s) will be created. You can also configure *default tags* for your deployment.

## VPC Flow Logs Destined to a Cloudwatch Log Group

`cdktf deploy vpc-flowlogs-loggroup`

## VPC Flow Logs Destined to a bucket in S3

`cdktf deploy vpc-flowlogs-s3`