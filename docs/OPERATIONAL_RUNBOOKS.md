# Operational Runbooks - Vernacular Artisan Catalog

## Table of Contents

1. [Overview](#overview)
2. [CloudWatch Monitoring and Alerting](#cloudwatch-monitoring-and-alerting)
3. [Troubleshooting Common Issues](#troubleshooting-common-issues)
4. [Backup and Recovery Procedures](#backup-and-recovery-procedures)
5. [Cost Optimization Strategies](#cost-optimization-strategies)
6. [Incident Response Procedures](#incident-response-procedures)
7. [Maintenance Windows](#maintenance-windows)
8. [Escalation Procedures](#escalation-procedures)

---

## Overview

This document provides comprehensive operational runbooks for the Vernacular Artisan Catalog system. It covers monitoring, troubleshooting, backup/recovery, and cost optimization procedures.

### System Architecture Summary

- **API Layer**: API Gateway + Lambda (API Handler)
- **Processing Pipeline**: SQS Queue + Lambda (Orchestrator)
- **AI Services**: Sagemaker (Vision + ASR), Bedrock (LLM)
- **Storage**: S3 (Raw + Enhanced Media), DynamoDB (Metadata)
- **Observability**: CloudWatch (Metrics, Logs, Alarms), X-Ray (Tracing)
- **Notifications**: SNS (Alarms)

### Key Metrics

| Metric | Normal Range | Alert Threshold | Critical Threshold |
|--------|--------------|-----------------|-------------------|
| Processing Latency | < 60s | > 60s | > 120s |
| API Response Time | < 500ms | > 1s | > 3s |
| Error Rate | < 1% | > 5% | > 10% |
| Queue Depth | < 50 | > 100 | > 500 |
| Processing Cost | < $0.30 | > $0.50 | > $1.00 |
| Lambda Duration | < 45s | > 60s | > 90s |

---

## CloudWatch Monitoring and Alerting

### 1. CloudWatch Dashboard

**Access Dashboard:**
```
https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1#dashboards:name=ArtisanCatalogSystemHealth
```

**Dashboard Widgets:**

1. **Queue Depth** - Monitors SQS queue backlog
   - Normal: < 50 messages
   - Warning: 50-100 messages
   - Critical: > 100 messages

2. **Processing Latency** - End-to-end processing time
   - P50: < 30s
   - P95: < 60s
   - P99: < 120s

3. **Error Rate** - Percentage of failed operations
   - Target: < 1%
   - Warning: 1-5%
   - Critical: > 5%

4. **Lambda Duration** - Function execution time
   - API Handler: < 30s
   - Orchestrator: < 60s

5. **ONDC Submission Status** - Success/failure counts
   - Success rate target: > 95%

6. **Processing Cost** - Per-entry cost tracking
   - Target: < $0.30
   - Warning: $0.30-$0.50
   - Critical: > $0.50

### 2. CloudWatch Metrics

**Custom Namespace:** `VernacularArtisanCatalog`

**Key Metrics:**

| Metric Name | Dimensions | Unit | Description |
|-------------|------------|------|-------------|
| `QueueDepth` | - | Count | Number of messages in SQS queue |
| `ProcessingLatency` | Operation, TenantId | Milliseconds | Operation execution time |
| `ErrorCount` | Operation, ErrorType, TenantId | Count | Number of errors |
| `SuccessCount` | Operation, TenantId | Count | Number of successful operations |
| `ProcessingCost` | Operation, TenantId | None | Cost per operation ($) |
| `ONDCSubmissionStatus` | Status, TenantId | Count | ONDC submission outcomes |

**Viewing Metrics:**
```bash
# View queue depth
aws cloudwatch get-metric-statistics \
  --namespace VernacularArtisanCatalog \
  --metric-name QueueDepth \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# View error rate
aws cloudwatch get-metric-statistics \
  --namespace VernacularArtisanCatalog \
  --metric-name ErrorCount \
  --dimensions Name=Operation,Value=sagemaker \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### 3. CloudWatch Alarms

**Configured Alarms:**

#### 3.1 OrchestratorDurationAlarm
- **Metric**: Lambda Duration (Orchestrator)
- **Threshold**: > 60 seconds
- **Evaluation**: 1 datapoint in 5 minutes
- **Action**: SNS notification
- **Severity**: Warning
- **Runbook**: [High Processing Latency](#runbook-high-processing-latency)

#### 3.2 ApiHandlerDurationAlarm
- **Metric**: Lambda Duration (API Handler)
- **Threshold**: > 30 seconds
- **Evaluation**: 1 datapoint in 5 minutes
- **Action**: SNS notification
- **Severity**: Warning
- **Runbook**: [Slow API Response](#runbook-slow-api-response)

#### 3.3 ErrorRateAlarm
- **Metric**: ErrorCount / (ErrorCount + SuccessCount)
- **Threshold**: > 5%
- **Evaluation**: 2 datapoints in 10 minutes
- **Action**: SNS notification
- **Severity**: Critical
- **Runbook**: [High Error Rate](#runbook-high-error-rate)

#### 3.4 CostThresholdAlarm
- **Metric**: ProcessingCost
- **Threshold**: > $0.50 per entry
- **Evaluation**: 1 datapoint in 5 minutes
- **Action**: SNS notification
- **Severity**: Warning
- **Runbook**: [High Processing Cost](#runbook-high-processing-cost)

#### 3.5 QueueDepthAlarm
- **Metric**: QueueDepth
- **Threshold**: > 100 messages
- **Evaluation**: 2 datapoints in 10 minutes
- **Action**: SNS notification, Auto-scaling trigger
- **Severity**: Warning
- **Runbook**: [Queue Backlog](#runbook-queue-backlog)

#### 3.6 DLQMessagesAlarm
- **Metric**: ApproximateNumberOfMessagesVisible (DLQ)
- **Threshold**: > 0 messages
- **Evaluation**: 1 datapoint in 5 minutes
- **Action**: SNS notification
- **Severity**: Critical
- **Runbook**: [Dead Letter Queue Messages](#runbook-dead-letter-queue-messages)

#### 3.7 LambdaErrorsAlarm
- **Metric**: Lambda Errors
- **Threshold**: > 5 errors
- **Evaluation**: 1 datapoint in 5 minutes
- **Action**: SNS notification
- **Severity**: Critical
- **Runbook**: [Lambda Function Errors](#runbook-lambda-function-errors)

**Managing Alarms:**
```bash
# List all alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix artisan-catalog

# Disable alarm temporarily (during maintenance)
aws cloudwatch disable-alarm-actions \
  --alarm-names artisan-catalog-error-rate

# Re-enable alarm
aws cloudwatch enable-alarm-actions \
  --alarm-names artisan-catalog-error-rate

# Update alarm threshold
aws cloudwatch put-metric-alarm \
  --alarm-name artisan-catalog-error-rate \
  --threshold 10  # Increase threshold to 10%
```

### 4. CloudWatch Logs

**Log Groups:**
- `/aws/lambda/artisan-catalog-api-handler` - API Gateway Lambda logs
- `/aws/lambda/artisan-catalog-orchestrator` - Processing Lambda logs
- `/aws/apigateway/artisan-catalog-api` - API Gateway execution logs

**Log Retention:** 7 days (configurable)

**Useful Log Insights Queries:**

#### Query 1: Error Analysis
```sql
fields @timestamp, @message, tracking_id, error_type
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

#### Query 2: Processing Latency by Stage
```sql
fields @timestamp, tracking_id, stage, latency_ms
| filter @message like /Stage completed/
| stats avg(latency_ms), max(latency_ms), min(latency_ms) by stage, bin(5m)
```

#### Query 3: ONDC Submission Failures
```sql
fields @timestamp, tracking_id, error_message, ondc_response
| filter stage = "ondc_submission" and status = "failed"
| sort @timestamp desc
| limit 50
```

#### Query 4: High Cost Entries
```sql
fields @timestamp, tracking_id, processing_cost, tenant_id
| filter processing_cost > 0.50
| sort processing_cost desc
| limit 20
```

#### Query 5: Tenant-Specific Errors
```sql
fields @timestamp, tracking_id, tenant_id, error_type
| filter tenant_id = "tenant-001" and @message like /ERROR/
| stats count() by error_type, bin(1h)
```

**Accessing Logs:**
```bash
# Stream logs in real-time
aws logs tail /aws/lambda/artisan-catalog-orchestrator --follow

# Filter logs by pattern
aws logs filter-log-events \
  --log-group-name /aws/lambda/artisan-catalog-orchestrator \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# Export logs to S3
aws logs create-export-task \
  --log-group-name /aws/lambda/artisan-catalog-orchestrator \
  --from $(date -u -d '1 day ago' +%s)000 \
  --to $(date -u +%s)000 \
  --destination logs-export-bucket \
  --destination-prefix orchestrator-logs/
```

### 5. X-Ray Distributed Tracing

**Access X-Ray Console:**
```
https://console.aws.amazon.com/xray/home?region=ap-south-1#/traces
```

**Service Map:**
- View end-to-end request flow
- Identify bottlenecks and latency sources
- Detect error patterns

**Trace Filtering:**
```
# Filter by tracking ID
annotation.tracking_id = "track-123"

# Filter by tenant
annotation.tenant_id = "tenant-001"

# Filter by errors
annotation.status = "error"

# Filter by operation
annotation.operation = "sagemaker"

# Filter by latency
responsetime > 60
```

**Analyzing Traces:**
```bash
# Get trace summaries
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --filter-expression 'annotation.status = "error"'

# Get specific trace details
aws xray batch-get-traces \
  --trace-ids TRACE_ID_1 TRACE_ID_2
```

---

## Troubleshooting Common Issues

### Runbook: High Processing Latency

**Symptoms:**
- OrchestratorDurationAlarm triggered
- Processing time > 60 seconds
- User complaints about slow catalog creation

**Diagnosis Steps:**

1. **Check X-Ray traces** to identify slow component:
   ```bash
   # Find slow traces
   aws xray get-trace-summaries \
     --start-time $(date -u -d '1 hour ago' +%s) \
     --end-time $(date -u +%s) \
     --filter-expression 'duration > 60'
   ```

2. **Review CloudWatch metrics** for each stage:
   - Sagemaker latency
   - Bedrock latency
   - ONDC submission latency
   - Image enhancement latency

3. **Check Sagemaker endpoint status**:
   ```bash
   aws sagemaker describe-endpoint \
     --endpoint-name artisan-vision-asr-endpoint
   ```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Sagemaker cold start | Enable endpoint auto-scaling or use provisioned instances |
| Large image files | Implement image resizing before Sagemaker inference |
| Bedrock throttling | Implement exponential backoff, request quota increase |
| ONDC API slow | Implement timeout and retry logic, contact ONDC support |
| Network latency | Deploy Lambda in VPC closer to external services |

**Immediate Actions:**
1. Scale up Sagemaker endpoint instances
2. Increase Lambda timeout temporarily
3. Enable CloudWatch Insights to identify bottleneck

**Long-term Solutions:**
1. Optimize image preprocessing
2. Implement caching for repeated operations
3. Use Bedrock batch inference for multiple entries
4. Consider async ONDC submission with webhooks

### Runbook: Slow API Response

**Symptoms:**
- ApiHandlerDurationAlarm triggered
- API response time > 30 seconds
- Mobile app timeouts

**Diagnosis Steps:**

1. **Check API Gateway metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApiGateway \
     --metric-name Latency \
     --dimensions Name=ApiName,Value=artisan-catalog-api \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average,Maximum
   ```

2. **Review Lambda logs** for API handler:
   ```bash
   aws logs tail /aws/lambda/artisan-catalog-api-handler --follow
   ```

3. **Check DynamoDB throttling**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name UserErrors \
     --dimensions Name=TableName,Value=CatalogProcessingRecords \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum
   ```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Lambda cold start | Enable provisioned concurrency for API handler |
| DynamoDB throttling | Switch to on-demand billing or increase provisioned capacity |
| S3 presigned URL generation slow | Cache S3 client, optimize IAM role |
| Large DynamoDB queries | Add GSI for efficient queries, implement pagination |

**Immediate Actions:**
1. Enable provisioned concurrency (1-2 instances)
2. Switch DynamoDB to on-demand billing
3. Increase API Gateway timeout

**Long-term Solutions:**
1. Implement API response caching
2. Optimize DynamoDB schema and indexes
3. Use Lambda@Edge for global distribution

### Runbook: High Error Rate

**Symptoms:**
- ErrorRateAlarm triggered
- Error rate > 5%
- Multiple failed catalog entries

**Diagnosis Steps:**

1. **Identify error types** from CloudWatch Logs:
   ```sql
   fields @timestamp, error_type, count(*) as error_count
   | filter @message like /ERROR/
   | stats count() by error_type, bin(5m)
   ```

2. **Check error distribution** by stage:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace VernacularArtisanCatalog \
     --metric-name ErrorCount \
     --dimensions Name=Operation,Value=sagemaker \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum
   ```

3. **Review X-Ray traces** for error patterns:
   ```
   annotation.status = "error"
   ```

**Common Errors & Solutions:**

| Error Type | Cause | Solution |
|------------|-------|----------|
| `SagemakerEndpointNotFound` | Endpoint deleted or wrong name | Verify endpoint exists, update Lambda env var |
| `BedrockThrottlingException` | Rate limit exceeded | Implement exponential backoff, request quota increase |
| `ONDCValidationError` | Invalid schema | Review ONDC payload, fix schema mapping |
| `S3AccessDenied` | IAM permissions issue | Verify Lambda role has S3 permissions |
| `DynamoDBProvisionedThroughputExceeded` | Capacity exceeded | Switch to on-demand or increase capacity |
| `TimeoutError` | Operation took too long | Increase Lambda timeout, optimize processing |

**Immediate Actions:**
1. Check external service status (Sagemaker, Bedrock, ONDC)
2. Review recent code deployments
3. Verify IAM permissions
4. Check for API quota limits

**Long-term Solutions:**
1. Implement circuit breaker pattern
2. Add retry logic with exponential backoff
3. Implement graceful degradation
4. Add input validation before processing

### Runbook: High Processing Cost

**Symptoms:**
- CostThresholdAlarm triggered
- Processing cost > $0.50 per entry
- Budget alerts

**Diagnosis Steps:**

1. **Identify cost breakdown** by operation:
   ```sql
   fields @timestamp, tracking_id, operation, cost
   | filter processing_cost > 0.50
   | stats sum(cost) by operation
   ```

2. **Check Sagemaker usage**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/SageMaker \
     --metric-name ModelInvocations \
     --dimensions Name=EndpointName,Value=artisan-vision-asr-endpoint \
     --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 3600 \
     --statistics Sum
   ```

3. **Review Bedrock token usage**:
   - Check CloudWatch Logs for token counts
   - Analyze prompt sizes

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Large images sent to Sagemaker | Resize images before inference (max 1920px) |
| Verbose Bedrock prompts | Optimize prompts, reduce token usage |
| Multiple retries | Fix root cause of failures to reduce retries |
| Sagemaker instance over-provisioned | Right-size instance type (e.g., ml.g4dn.xlarge → ml.t2.medium) |
| Bedrock using expensive model | Switch to cheaper model (e.g., Claude Instant) |

**Immediate Actions:**
1. Review recent high-cost entries
2. Implement image resizing before Sagemaker
3. Optimize Bedrock prompts
4. Enable cost allocation tags

**Long-term Solutions:**
1. Implement batch processing for multiple entries
2. Use Sagemaker Serverless for variable traffic
3. Cache Bedrock responses for similar inputs
4. Implement cost-aware routing (use cheaper models when possible)

### Runbook: Queue Backlog

**Symptoms:**
- QueueDepthAlarm triggered
- Queue depth > 100 messages
- Slow catalog processing

**Diagnosis Steps:**

1. **Check queue metrics**:
   ```bash
   aws sqs get-queue-attributes \
     --queue-url https://sqs.ap-south-1.amazonaws.com/ACCOUNT/catalog-processing-queue \
     --attribute-names All
   ```

2. **Check Lambda concurrency**:
   ```bash
   aws lambda get-function-concurrency \
     --function-name artisan-catalog-orchestrator
   ```

3. **Review processing rate**:
   ```sql
   fields @timestamp, tracking_id, processing_time
   | filter @message like /Processing completed/
   | stats count() by bin(5m)
   ```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Lambda throttling | Increase reserved concurrency |
| Slow processing | Optimize Lambda code, increase memory |
| Sagemaker endpoint overloaded | Scale up endpoint instances |
| Sudden traffic spike | Enable auto-scaling, increase batch size |

**Immediate Actions:**
1. Increase Lambda reserved concurrency:
   ```bash
   aws lambda put-function-concurrency \
     --function-name artisan-catalog-orchestrator \
     --reserved-concurrent-executions 100
   ```

2. Scale up Sagemaker endpoint:
   ```bash
   aws sagemaker update-endpoint-weights-and-capacities \
     --endpoint-name artisan-vision-asr-endpoint \
     --desired-weights-and-capacities VariantName=AllTraffic,DesiredInstanceCount=3
   ```

3. Increase SQS batch size:
   ```bash
   aws lambda update-event-source-mapping \
     --uuid EVENT_SOURCE_MAPPING_UUID \
     --batch-size 20
   ```

**Long-term Solutions:**
1. Implement auto-scaling for Lambda and Sagemaker
2. Use SQS FIFO queue for ordered processing
3. Implement priority queuing for urgent entries
4. Add queue depth monitoring and alerting

### Runbook: Dead Letter Queue Messages

**Symptoms:**
- DLQMessagesAlarm triggered
- Messages in dead letter queue
- Catalog entries not processing

**Diagnosis Steps:**

1. **Check DLQ messages**:
   ```bash
   aws sqs receive-message \
     --queue-url https://sqs.ap-south-1.amazonaws.com/ACCOUNT/catalog-processing-dlq \
     --max-number-of-messages 10
   ```

2. **Analyze message content**:
   - Extract tracking_id
   - Review error details
   - Check message attributes

3. **Query DynamoDB for entry status**:
   ```bash
   aws dynamodb get-item \
     --table-name CatalogProcessingRecords \
     --key '{"tracking_id": {"S": "TRACKING_ID"}}'
   ```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Invalid message format | Fix message serialization, redrive messages |
| Persistent processing error | Fix root cause, manually reprocess |
| Lambda timeout | Increase timeout, optimize code |
| External service unavailable | Wait for service recovery, redrive messages |

**Immediate Actions:**
1. Review DLQ messages for patterns
2. Fix root cause of failures
3. Redrive messages to main queue:
   ```bash
   aws sqs start-message-move-task \
     --source-arn arn:aws:sqs:ap-south-1:ACCOUNT:catalog-processing-dlq \
     --destination-arn arn:aws:sqs:ap-south-1:ACCOUNT:catalog-processing-queue
   ```

4. Notify affected artisans

**Long-term Solutions:**
1. Implement better error handling
2. Add message validation before queuing
3. Implement manual review workflow for DLQ messages
4. Add DLQ monitoring dashboard

### Runbook: Lambda Function Errors

**Symptoms:**
- LambdaErrorsAlarm triggered
- Lambda invocation failures
- CloudWatch Logs showing exceptions

**Diagnosis Steps:**

1. **Check Lambda error metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Errors \
     --dimensions Name=FunctionName,Value=artisan-catalog-orchestrator \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum
   ```

2. **Review Lambda logs**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/artisan-catalog-orchestrator \
     --filter-pattern "ERROR" \
     --start-time $(date -u -d '1 hour ago' +%s)000
   ```

3. **Check Lambda configuration**:
   ```bash
   aws lambda get-function-configuration \
     --function-name artisan-catalog-orchestrator
   ```

**Common Errors & Solutions:**

| Error Type | Cause | Solution |
|------------|-------|----------|
| `ImportError` | Missing dependency | Update Lambda layer, redeploy |
| `MemoryError` | Insufficient memory | Increase Lambda memory allocation |
| `TimeoutError` | Execution exceeded timeout | Increase timeout, optimize code |
| `PermissionError` | IAM role missing permissions | Update IAM policy |
| `ConnectionError` | Network connectivity issue | Check VPC configuration, security groups |

**Immediate Actions:**
1. Rollback to previous working version:
   ```bash
   aws lambda update-function-code \
     --function-name artisan-catalog-orchestrator \
     --s3-bucket lambda-deployments \
     --s3-key orchestrator-v1.0.0.zip
   ```

2. Increase Lambda resources:
   ```bash
   aws lambda update-function-configuration \
     --function-name artisan-catalog-orchestrator \
     --memory-size 2048 \
     --timeout 600
   ```

3. Check environment variables:
   ```bash
   aws lambda get-function-configuration \
     --function-name artisan-catalog-orchestrator \
     --query 'Environment.Variables'
   ```

**Long-term Solutions:**
1. Implement comprehensive unit tests
2. Add integration tests in CI/CD pipeline
3. Use Lambda versions and aliases for safe deployments
4. Implement canary deployments

---

## Backup and Recovery Procedures

### 1. DynamoDB Backup and Recovery

**Point-in-Time Recovery (PITR):**

DynamoDB PITR is enabled for all tables, allowing recovery to any point in the last 35 days.

**Verify PITR Status:**
```bash
aws dynamodb describe-continuous-backups \
  --table-name CatalogProcessingRecords
```

**Restore Table to Point in Time:**
```bash
# Restore to specific timestamp
aws dynamodb restore-table-to-point-in-time \
  --source-table-name CatalogProcessingRecords \
  --target-table-name CatalogProcessingRecords-Restored \
  --restore-date-time 2024-01-15T10:30:00Z

# Restore to latest restorable time
aws dynamodb restore-table-to-point-in-time \
  --source-table-name CatalogProcessingRecords \
  --target-table-name CatalogProcessingRecords-Restored \
  --use-latest-restorable-time
```

**On-Demand Backups:**

Create manual backups before major changes:
```bash
# Create backup
aws dynamodb create-backup \
  --table-name CatalogProcessingRecords \
  --backup-name CatalogProcessingRecords-PreDeployment-$(date +%Y%m%d)

# List backups
aws dynamodb list-backups \
  --table-name CatalogProcessingRecords

# Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name CatalogProcessingRecords-Restored \
  --backup-arn arn:aws:dynamodb:ap-south-1:ACCOUNT:table/CatalogProcessingRecords/backup/BACKUP_ID
```

**Backup Schedule:**
- **PITR**: Continuous (automatic)
- **Manual backups**: Before major deployments
- **Retention**: 35 days (PITR), indefinite (manual backups)

### 2. S3 Backup and Recovery

**Versioning:**

S3 versioning is enabled for both raw and enhanced media buckets.

**Verify Versioning:**
```bash
aws s3api get-bucket-versioning \
  --bucket artisan-catalog-raw-media-ACCOUNT
```

**Recover Deleted Object:**
```bash
# List object versions
aws s3api list-object-versions \
  --bucket artisan-catalog-raw-media-ACCOUNT \
  --prefix path/to/object.jpg

# Restore specific version
aws s3api copy-object \
  --bucket artisan-catalog-raw-media-ACCOUNT \
  --copy-source artisan-catalog-raw-media-ACCOUNT/path/to/object.jpg?versionId=VERSION_ID \
  --key path/to/object.jpg
```

**Cross-Region Replication (Optional):**

For disaster recovery, enable cross-region replication:
```bash
# Create replication configuration
aws s3api put-bucket-replication \
  --bucket artisan-catalog-raw-media-ACCOUNT \
  --replication-configuration file://replication-config.json
```

**replication-config.json:**
```json
{
  "Role": "arn:aws:iam::ACCOUNT:role/S3ReplicationRole",
  "Rules": [{
    "Status": "Enabled",
    "Priority": 1,
    "Filter": {},
    "Destination": {
      "Bucket": "arn:aws:s3:::artisan-catalog-raw-media-backup",
      "ReplicationTime": {
        "Status": "Enabled",
        "Time": {
          "Minutes": 15
        }
      }
    }
  }]
}
```

**Backup Schedule:**
- **Versioning**: Continuous (automatic)
- **Lifecycle**: 30-day retention (automatic deletion)
- **Cross-region replication**: Real-time (if enabled)

### 3. Lambda Function Backup

**Version Control:**

Lambda code is stored in Git repository. All deployments are versioned.

**Create Lambda Version:**
```bash
# Publish new version
aws lambda publish-version \
  --function-name artisan-catalog-orchestrator \
  --description "Production release v1.2.0"

# List versions
aws lambda list-versions-by-function \
  --function-name artisan-catalog-orchestrator
```

**Rollback to Previous Version:**
```bash
# Update alias to point to previous version
aws lambda update-alias \
  --function-name artisan-catalog-orchestrator \
  --name prod \
  --function-version 5  # Previous working version
```

**Export Lambda Configuration:**
```bash
# Export function configuration
aws lambda get-function \
  --function-name artisan-catalog-orchestrator \
  > lambda-config-backup.json

# Export function code
aws lambda get-function \
  --function-name artisan-catalog-orchestrator \
  --query 'Code.Location' \
  --output text | xargs wget -O lambda-code-backup.zip
```

### 4. Disaster Recovery Procedures

**Recovery Time Objective (RTO):** 4 hours
**Recovery Point Objective (RPO):** 1 hour

**Disaster Scenarios:**

#### Scenario 1: Complete Region Failure

**Recovery Steps:**
1. Deploy infrastructure in backup region (us-east-1):
   ```bash
   cd backend/infrastructure/cdk
   cdk deploy --context region=us-east-1
   ```

2. Restore DynamoDB tables from backup:
   ```bash
   aws dynamodb restore-table-from-backup \
     --target-table-name CatalogProcessingRecords \
     --backup-arn BACKUP_ARN \
     --region us-east-1
   ```

3. Sync S3 data from replicated bucket (if enabled)

4. Update DNS/API Gateway custom domain to point to new region

5. Verify system health and run smoke tests

**Estimated Recovery Time:** 3-4 hours

#### Scenario 2: Data Corruption

**Recovery Steps:**
1. Identify corruption timestamp
2. Restore DynamoDB table to point before corruption:
   ```bash
   aws dynamodb restore-table-to-point-in-time \
     --source-table-name CatalogProcessingRecords \
     --target-table-name CatalogProcessingRecords-Clean \
     --restore-date-time 2024-01-15T09:00:00Z
   ```

3. Verify restored data integrity
4. Swap table names (requires downtime):
   ```bash
   # Rename current table
   aws dynamodb update-table \
     --table-name CatalogProcessingRecords \
     --new-table-name CatalogProcessingRecords-Corrupted
   
   # Rename restored table
   aws dynamodb update-table \
     --table-name CatalogProcessingRecords-Clean \
     --new-table-name CatalogProcessingRecords
   ```

5. Update Lambda environment variables if needed
6. Resume operations

**Estimated Recovery Time:** 1-2 hours

#### Scenario 3: Accidental Deletion

**Recovery Steps:**
1. For S3 objects, restore from version history (see S3 recovery above)
2. For DynamoDB items, restore table to point before deletion
3. For Lambda functions, redeploy from Git repository
4. Verify restored resources

**Estimated Recovery Time:** 30 minutes - 1 hour

---

## Cost Optimization Strategies

### 1. Lambda Cost Optimization

**Right-Sizing Memory:**

Lambda costs are based on memory allocation and execution time. Optimize memory for best price/performance.

**Analyze Memory Usage:**
```bash
# Get Lambda insights metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=artisan-catalog-orchestrator \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average,Maximum
```

**Optimization Guidelines:**
- If max memory usage < 70% of allocated: Reduce memory
- If max memory usage > 90% of allocated: Increase memory
- Test different memory sizes to find optimal cost/performance

**Example Optimization:**
```bash
# Current: 1024MB, avg usage: 600MB
# Reduce to 768MB
aws lambda update-function-configuration \
  --function-name artisan-catalog-orchestrator \
  --memory-size 768
```

**Estimated Savings:** 25% reduction in Lambda costs

**Provisioned Concurrency:**
- Only use for API handler if cold starts are critical
- Cost: ~$0.015/hour per instance
- Alternative: Use Lambda SnapStart (Java) or container image caching

### 2. DynamoDB Cost Optimization

**On-Demand vs. Provisioned Capacity:**

**Current:** On-demand (pay-per-request)
**When to switch:** Predictable, consistent traffic

**Cost Comparison:**
- On-demand: $1.25 per million writes, $0.25 per million reads
- Provisioned: $0.00065 per WCU-hour, $0.00013 per RCU-hour

**Switch to Provisioned:**
```bash
aws dynamodb update-table \
  --table-name CatalogProcessingRecords \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=5
```

**Enable Auto-Scaling:**
```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/CatalogProcessingRecords \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 \
  --max-capacity 50

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/CatalogProcessingRecords \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-name dynamodb-write-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "DynamoDBWriteCapacityUtilization"
    }
  }'
```

**Estimated Savings:** 30-50% for predictable workloads

**Table Class Optimization:**

For infrequently accessed data, use DynamoDB Standard-IA:
```bash
aws dynamodb update-table \
  --table-name CatalogProcessingRecords \
  --table-class STANDARD_INFREQUENT_ACCESS
```

**Estimated Savings:** 60% on storage costs

### 3. Sagemaker Cost Optimization

**Auto-Scaling:**

Scale Sagemaker endpoint based on invocation count.

**Configure Auto-Scaling:**
```python
import boto3

client = boto3.client('application-autoscaling')

# Register scalable target
client.register_scalable_target(
    ServiceNamespace='sagemaker',
    ResourceId='endpoint/artisan-vision-asr-endpoint/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    MinCapacity=1,
    MaxCapacity=5
)

# Create scaling policy
client.put_scaling_policy(
    PolicyName='sagemaker-invocation-scaling',
    ServiceNamespace='sagemaker',
    ResourceId='endpoint/artisan-vision-asr-endpoint/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyType='TargetTrackingScaling',
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 100.0,  # Target 100 invocations per instance
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
        },
        'ScaleInCooldown': 300,
        'ScaleOutCooldown': 60
    }
)
```

**Estimated Savings:** 40-60% during low-traffic periods

**Serverless Inference:**

For variable/low traffic, use Sagemaker Serverless:
```python
import boto3

sagemaker = boto3.client('sagemaker')

# Create serverless endpoint config
sagemaker.create_endpoint_config(
    EndpointConfigName='artisan-serverless-config',
    ProductionVariants=[{
        'VariantName': 'AllTraffic',
        'ModelName': 'artisan-vision-asr-model',
        'ServerlessConfig': {
            'MemorySizeInMB': 4096,
            'MaxConcurrency': 10
        }
    }]
)

# Update endpoint
sagemaker.update_endpoint(
    EndpointName='artisan-vision-asr-endpoint',
    EndpointConfigName='artisan-serverless-config'
)
```

**Cost Comparison:**
- Real-time: ml.g4dn.xlarge = $0.736/hour = $530/month (24/7)
- Serverless: $0.20 per 1M inference seconds = ~$50/month (10,000 entries)

**Estimated Savings:** 90% for low-traffic scenarios

**Instance Type Optimization:**

Test different instance types for best price/performance:
- ml.g4dn.xlarge: $0.736/hour (GPU, high performance)
- ml.m5.xlarge: $0.269/hour (CPU, moderate performance)
- ml.t3.medium: $0.083/hour (CPU, low performance)

**Recommendation:** Use ml.m5.xlarge for cost-effective performance

### 4. S3 Cost Optimization

**Intelligent Tiering:**

Automatically move objects to cheaper storage classes.

**Enable Intelligent Tiering:**
```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket artisan-catalog-raw-media-ACCOUNT \
  --id intelligent-tiering-config \
  --intelligent-tiering-configuration '{
    "Id": "intelligent-tiering-config",
    "Status": "Enabled",
    "Tierings": [
      {
        "Days": 90,
        "AccessTier": "ARCHIVE_ACCESS"
      },
      {
        "Days": 180,
        "AccessTier": "DEEP_ARCHIVE_ACCESS"
      }
    ]
  }'
```

**Lifecycle Policies:**

Current policy: 30-day expiration (privacy requirement)

**Optimize for Cost:**
- Days 0-7: Standard storage
- Days 7-30: Intelligent Tiering
- Day 30: Delete (privacy requirement)

**Update Lifecycle Policy:**
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket artisan-catalog-raw-media-ACCOUNT \
  --lifecycle-configuration file://lifecycle-policy.json
```

**lifecycle-policy.json:**
```json
{
  "Rules": [{
    "Id": "media-lifecycle",
    "Status": "Enabled",
    "Filter": {},
    "Transitions": [{
      "Days": 7,
      "StorageClass": "INTELLIGENT_TIERING"
    }],
    "Expiration": {
      "Days": 30
    }
  }]
}
```

**Estimated Savings:** 20-30% on storage costs

**Request Optimization:**

Reduce S3 request costs by batching operations:
- Use S3 Batch Operations for bulk processing
- Implement caching for frequently accessed objects
- Use CloudFront for media delivery (reduces S3 GET requests)

### 5. Bedrock Cost Optimization

**Prompt Optimization:**

Reduce token usage by optimizing prompts.

**Current Prompt Size:** ~1500 tokens
**Optimized Prompt Size:** ~800 tokens

**Optimization Techniques:**
1. Remove verbose instructions
2. Use concise examples
3. Eliminate redundant context
4. Use structured output format

**Example Optimization:**
```python
# Before (verbose)
prompt = """
You are an AI assistant helping to extract product attributes from artisan descriptions.
Please carefully analyze the following transcription and image analysis results.
Extract all relevant product attributes including category, material, color, dimensions, weight, and price.
Preserve any culturally significant terms in the original language.
Generate a short description (1-2 sentences) and a long description (3-4 sentences).
...
"""

# After (concise)
prompt = """
Extract product attributes from transcription and image analysis.
Required: category, material, color, price. Optional: dimensions, weight.
Preserve cultural terms. Output: JSON with short_desc (1-2 sentences), long_desc (3-4 sentences).
...
"""
```

**Estimated Savings:** 40-50% on Bedrock costs

**Model Selection:**

Use cheaper models when appropriate:
- Claude 3 Sonnet: $0.003 per 1K input tokens, $0.015 per 1K output tokens
- Claude 3 Haiku: $0.00025 per 1K input tokens, $0.00125 per 1K output tokens

**Recommendation:** Use Haiku for simple attribute extraction, Sonnet for complex transcreation

**Estimated Savings:** 90% for simple tasks

**Caching:**

Implement response caching for similar inputs:
```python
import hashlib
import json

def get_cached_response(cache_key):
    # Check DynamoDB cache
    response = dynamodb.get_item(
        TableName='BedrockResponseCache',
        Key={'cache_key': {'S': cache_key}}
    )
    return response.get('Item', {}).get('response')

def cache_response(cache_key, response):
    dynamodb.put_item(
        TableName='BedrockResponseCache',
        Item={
            'cache_key': {'S': cache_key},
            'response': {'S': json.dumps(response)},
            'ttl': {'N': str(int(time.time()) + 86400)}  # 24-hour TTL
        }
    )

# Usage
cache_key = hashlib.sha256(f"{transcription}:{image_analysis}".encode()).hexdigest()
cached = get_cached_response(cache_key)
if cached:
    return json.loads(cached)
else:
    response = bedrock.invoke_model(...)
    cache_response(cache_key, response)
    return response
```

**Estimated Savings:** 30-50% for repeated patterns

### 6. Overall Cost Monitoring

**Set Up Cost Allocation Tags:**
```bash
# Tag all resources
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    arn:aws:lambda:ap-south-1:ACCOUNT:function:artisan-catalog-* \
    arn:aws:dynamodb:ap-south-1:ACCOUNT:table/CatalogProcessingRecords \
    arn:aws:s3:::artisan-catalog-* \
  --tags Project=VernacularArtisanCatalog,Environment=Production,CostCenter=Engineering
```

**Create Cost Budget:**
```bash
aws budgets create-budget \
  --account-id ACCOUNT \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**budget.json:**
```json
{
  "BudgetName": "ArtisanCatalogMonthlyBudget",
  "BudgetLimit": {
    "Amount": "500",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": ["user:Project$VernacularArtisanCatalog"]
  }
}
```

**Cost Optimization Summary:**

| Optimization | Current Cost | Optimized Cost | Savings |
|--------------|--------------|----------------|---------|
| Lambda right-sizing | $2.50/month | $1.90/month | 24% |
| DynamoDB provisioned | $1.50/month | $0.75/month | 50% |
| Sagemaker serverless | $530/month | $50/month | 91% |
| S3 intelligent tiering | $2.30/month | $1.60/month | 30% |
| Bedrock optimization | $30/month | $15/month | 50% |
| **Total** | **$571/month** | **$74/month** | **87%** |

**Note:** Sagemaker serverless savings assume low-traffic scenario (10,000 entries/month). For high traffic, use auto-scaling instead.

---

## Incident Response Procedures

### Incident Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **P0 - Critical** | Complete system outage | 15 minutes | API Gateway down, all processing failed |
| **P1 - High** | Major functionality impaired | 1 hour | Sagemaker endpoint down, high error rate |
| **P2 - Medium** | Partial functionality impaired | 4 hours | Slow processing, queue backlog |
| **P3 - Low** | Minor issues, no user impact | 24 hours | Non-critical alarm, cosmetic issues |

### Incident Response Workflow

```
1. Detection → 2. Triage → 3. Investigation → 4. Mitigation → 5. Resolution → 6. Post-Mortem
```

### 1. Detection

**Automated Detection:**
- CloudWatch alarms trigger SNS notifications
- X-Ray detects anomalies in traces
- Lambda errors logged to CloudWatch

**Manual Detection:**
- User reports via support channels
- Monitoring dashboard review
- Scheduled health checks

### 2. Triage

**Initial Assessment:**
1. Determine severity level (P0-P3)
2. Identify affected components
3. Estimate user impact
4. Assign incident commander

**Triage Checklist:**
- [ ] Severity level assigned
- [ ] Incident commander assigned
- [ ] Stakeholders notified
- [ ] War room established (for P0/P1)
- [ ] Initial investigation started

### 3. Investigation

**Investigation Steps:**
1. Review CloudWatch dashboard
2. Check X-Ray traces for errors
3. Review CloudWatch Logs

**Post-Mortem Template:**

```markdown
# Incident Post-Mortem: [Incident Title]

## Incident Summary
- **Date**: YYYY-MM-DD
- **Duration**: X hours
- **Severity**: P0/P1/P2/P3
- **Impact**: Description of user impact

## Timeline
- HH:MM - Incident detected
- HH:MM - Investigation started
- HH:MM - Root cause identified
- HH:MM - Mitigation applied
- HH:MM - Incident resolved

## Root Cause
Detailed explanation of what caused the incident.

## Resolution
Description of how the incident was resolved.

## Action Items
1. [ ] Action item 1 (Owner: Name, Due: Date)
2. [ ] Action item 2 (Owner: Name, Due: Date)

## Lessons Learned
- What went well
- What could be improved
- Preventive measures
```

**Post-Mortem Review:**
- Conduct within 48 hours of resolution
- Include all stakeholders
- Focus on learning, not blame
- Document action items
- Track action item completion

### Communication Templates

**Incident Notification (P0/P1):**
```
Subject: [P0/P1] Vernacular Artisan Catalog - [Brief Description]

We are currently experiencing [issue description].

Impact: [User impact description]
Status: Investigating / Mitigating / Resolved
ETA: [Estimated resolution time]

We will provide updates every [30 minutes / 1 hour].

Incident Commander: [Name]
```

**Resolution Notification:**
```
Subject: [RESOLVED] Vernacular Artisan Catalog - [Brief Description]

The incident has been resolved.

Root Cause: [Brief explanation]
Resolution: [What was done]
Duration: [Total incident duration]

A detailed post-mortem will be shared within 48 hours.

Thank you for your patience.
```

---

## Maintenance Windows

### Scheduled Maintenance

**Maintenance Schedule:**
- **Frequency**: Monthly (first Sunday of each month)
- **Time**: 02:00 - 06:00 IST (low-traffic period)
- **Duration**: Up to 4 hours
- **Notification**: 7 days advance notice

**Maintenance Activities:**
- Infrastructure updates (CDK stack updates)
- Lambda function deployments
- DynamoDB schema changes
- Sagemaker model updates
- Security patches

### Pre-Maintenance Checklist

- [ ] Maintenance window scheduled and communicated
- [ ] Backup all critical data (DynamoDB, S3)
- [ ] Test changes in staging environment
- [ ] Prepare rollback plan
- [ ] Disable CloudWatch alarms (non-critical)
- [ ] Enable maintenance mode (if needed)
- [ ] Notify stakeholders

### Maintenance Procedure

1. **Pre-Maintenance (T-1 hour):**
   - Verify backups completed
   - Disable non-critical alarms
   - Enable maintenance mode
   - Final stakeholder notification

2. **Maintenance (T+0):**
   - Execute planned changes
   - Monitor system health
   - Document any issues
   - Test critical functionality

3. **Post-Maintenance (T+4 hours):**
   - Verify all systems operational
   - Re-enable alarms
   - Disable maintenance mode
   - Send completion notification
   - Monitor for issues

### Post-Maintenance Checklist

- [ ] All changes deployed successfully
- [ ] System health verified
- [ ] Alarms re-enabled
- [ ] Maintenance mode disabled
- [ ] Stakeholders notified
- [ ] Documentation updated
- [ ] Post-maintenance monitoring (24 hours)

### Emergency Maintenance

For critical security patches or urgent fixes:
- **Notification**: 2 hours advance notice (if possible)
- **Time**: As soon as possible
- **Duration**: Minimize downtime
- **Communication**: Frequent updates

---

## Escalation Procedures

### Escalation Matrix

| Level | Role | Contact | Escalation Criteria |
|-------|------|---------|---------------------|
| **L1** | On-Call Engineer | Slack, PagerDuty | Initial response, basic troubleshooting |
| **L2** | Senior Engineer | Phone, Slack | L1 unable to resolve within 30 min (P0/P1) |
| **L3** | Engineering Manager | Phone | L2 unable to resolve within 1 hour (P0/P1) |
| **L4** | CTO / VP Engineering | Phone | Major outage > 2 hours, business impact |

### Escalation Triggers

**Automatic Escalation:**
- P0 incident not resolved within 1 hour
- P1 incident not resolved within 4 hours
- Multiple P1 incidents in 24 hours
- Data loss or security breach

**Manual Escalation:**
- On-call engineer requests escalation
- Incident commander determines need
- Stakeholder requests escalation

### External Escalation

**AWS Support:**
- **Support Plan**: Business or Enterprise
- **Contact**: AWS Support Console, Phone
- **When to Escalate**: AWS service issues, quota increases, technical guidance

**ONDC Support:**
- **Contact**: ONDC support portal, email
- **When to Escalate**: ONDC API issues, schema validation errors, integration problems

**Sagemaker/Bedrock Support:**
- **Contact**: AWS Support (AI/ML team)
- **When to Escalate**: Model performance issues, endpoint failures, quota limits

### On-Call Rotation

**Schedule:**
- 7-day rotation
- Primary and secondary on-call
- Handoff every Monday 09:00 IST

**On-Call Responsibilities:**
- Respond to alerts within 15 minutes
- Investigate and mitigate incidents
- Escalate when necessary
- Document incidents
- Participate in post-mortems

**On-Call Tools:**
- PagerDuty (alerting)
- Slack (communication)
- AWS Console (investigation)
- Runbooks (procedures)

---

## Appendix

### A. Useful Commands Reference

**CloudWatch:**
```bash
# View dashboard
aws cloudwatch get-dashboard --dashboard-name ArtisanCatalogSystemHealth

# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace VernacularArtisanCatalog \
  --metric-name ProcessingLatency \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Stream logs
aws logs tail /aws/lambda/artisan-catalog-orchestrator --follow
```

**Lambda:**
```bash
# Get function configuration
aws lambda get-function-configuration --function-name artisan-catalog-orchestrator

# Update function code
aws lambda update-function-code \
  --function-name artisan-catalog-orchestrator \
  --s3-bucket lambda-deployments \
  --s3-key orchestrator-latest.zip

# Invoke function
aws lambda invoke \
  --function-name artisan-catalog-orchestrator \
  --payload file://test-event.json \
  response.json
```

**DynamoDB:**
```bash
# Get item
aws dynamodb get-item \
  --table-name CatalogProcessingRecords \
  --key '{"tracking_id": {"S": "TRACKING_ID"}}'

# Query by GSI
aws dynamodb query \
  --table-name CatalogProcessingRecords \
  --index-name TenantIndex \
  --key-condition-expression "tenant_id = :tid" \
  --expression-attribute-values '{":tid": {"S": "tenant-001"}}'
```

**Sagemaker:**
```bash
# Describe endpoint
aws sagemaker describe-endpoint --endpoint-name artisan-vision-asr-endpoint

# Update endpoint
aws sagemaker update-endpoint \
  --endpoint-name artisan-vision-asr-endpoint \
  --endpoint-config-name new-config
```

### B. Contact Information

**Team Contacts:**
- On-Call Engineer: PagerDuty, Slack #oncall
- Engineering Manager: [email], [phone]
- DevOps Team: Slack #devops
- Security Team: Slack #security

**External Contacts:**
- AWS Support: AWS Support Console, 1-800-XXX-XXXX
- ONDC Support: support@ondc.org
- Vendor Support: [vendor contacts]

### C. Related Documentation

- [AWS Deployment Guide](./AWS_DEPLOYMENT.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Sagemaker Endpoint Deployment](./SAGEMAKER_ENDPOINT_DEPLOYMENT.md)
- [Observability Completion](./TASK17_OBSERVABILITY_COMPLETION.md)

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**Owner:** DevOps Team  
**Review Frequency:** Quarterly
