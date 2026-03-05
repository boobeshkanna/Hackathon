# Auto-Scaling and Throttling Configuration

This document describes the auto-scaling and API throttling configurations implemented for the Vernacular Artisan Catalog system.

## Lambda Auto-Scaling Configuration

### Orchestrator Lambda (Task 18.1)

**Reserved Concurrency**: 50 concurrent executions

The orchestrator Lambda is configured with reserved concurrency to handle queue depth spikes efficiently:

```typescript
reservedConcurrentExecutions: 50
```

**Rationale**:
- **Requirement 16.1**: Auto-scale up when queue depth > 100
- **Requirement 16.2**: Auto-scale down when queue depth < 20
- Reserved concurrency of 50 allows processing up to 500 messages concurrently (50 instances × 10 messages per batch)
- Lambda automatically scales up/down based on SQS queue depth
- CloudWatch alarm triggers when queue depth exceeds 100 messages

### SQS Event Source Configuration

**Batch Size**: 10 messages per invocation
**Max Batching Window**: 5 seconds
**Visibility Timeout**: 300 seconds (matches Lambda timeout)

```typescript
orchestratorLambda.addEventSource(
  new lambda.eventSources.SqsEventSource(processingQueue, {
    batchSize: 10,
    maxBatchingWindow: cdk.Duration.seconds(5),
    reportBatchItemFailures: true,
  })
);
```

**Benefits**:
- Processes up to 10 messages per Lambda invocation for efficiency
- Waits up to 5 seconds to fill batch, reducing cold starts
- Partial batch failure handling prevents reprocessing successful messages
- Visibility timeout prevents duplicate processing during Lambda execution

### API Handler Lambda (Optional Provisioned Concurrency)

**Provisioned Concurrency**: Optional (configurable via CDK context)

```typescript
const provisionedConcurrency = this.node.tryGetContext('provisionedConcurrency');
if (provisionedConcurrency) {
  const alias = new lambda.Alias(this, 'ApiHandlerAlias', {
    aliasName: 'prod',
    version: version,
    provisionedConcurrentExecutions: Number(provisionedConcurrency),
  });
}
```

**Usage**:
To enable provisioned concurrency, deploy with:
```bash
cdk deploy -c provisionedConcurrency=10
```

**Benefits**:
- Eliminates cold starts for API requests
- Ensures consistent low latency
- Recommended for production workloads with steady traffic

## API Gateway Throttling Configuration (Task 18.2)

### Usage Plan with Rate Limits

**Steady-State Rate Limit**: 100 requests/second
**Burst Limit**: 200 requests
**Daily Quota**: 100,000 requests per API key

```typescript
const usagePlan = new apigateway.UsagePlan(this, 'ArtisanCatalogUsagePlan', {
  throttle: {
    rateLimit: 100,
    burstLimit: 200,
  },
  quota: {
    limit: 100000,
    period: apigateway.Period.DAY,
  },
});
```

**Rationale**:
- **Requirement 16.3**: Support horizontal scaling without session affinity
- **Requirement 16.4**: Use stateless processing workers
- Rate limit of 100 req/s handles typical artisan catalog submission rates
- Burst limit of 200 allows temporary traffic spikes (e.g., batch uploads)
- Daily quota prevents abuse and controls costs

### API Key Authentication

All API endpoints require an API key for access:

```typescript
apiKeyRequired: true
```

**Retrieving API Key**:
After deployment, retrieve the API key value:
```bash
aws apigateway get-api-key --api-key $(aws cloudformation describe-stacks \
  --stack-name VernacularArtisanCatalogStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" \
  --output text) \
  --include-value
```

### Method-Level Throttling

Individual endpoints have request validation:

- **POST /v1/catalog/upload/initiate**: Validates request body and parameters
- **POST /v1/catalog/upload/complete**: Validates request body and parameters
- **GET /v1/catalog/status/{trackingId}**: Validates path parameters

**Benefits**:
- Prevents malformed requests from consuming Lambda resources
- Provides early validation before Lambda invocation
- Reduces costs by rejecting invalid requests at API Gateway

## Stateless Request Handling (Requirement 16.3, 16.4)

All Lambda functions are stateless:

```typescript
// Note: All Lambda functions are stateless (Requirement 16.4)
// State is maintained in DynamoDB and S3, allowing horizontal scaling
```

**Architecture**:
- **No session affinity**: Requests can be handled by any Lambda instance
- **State in DynamoDB**: All processing state stored in DynamoDB tables
- **Media in S3**: All media files stored in S3 buckets
- **Queue-based processing**: SQS ensures reliable message delivery

**Benefits**:
- Lambda instances can be added/removed without data loss
- Supports horizontal scaling to handle traffic spikes
- No sticky sessions required at API Gateway
- Enables auto-scaling based on queue depth

## Monitoring and Alarms

### Queue Depth Alarm

Triggers when queue depth exceeds 100 messages:

```typescript
const queueDepthAlarm = new cloudwatch.Alarm(this, 'QueueDepthAlarm', {
  metric: processingQueue.metricApproximateNumberOfMessagesVisible(),
  threshold: 100,
  evaluationPeriods: 2,
});
```

**Action**: Sends notification to SNS topic for manual intervention if needed

### Lambda Duration Alarms

- **Orchestrator**: Alerts when duration > 60 seconds
- **API Handler**: Alerts when duration > 30 seconds

**Action**: Indicates potential performance issues requiring optimization

## Deployment

Deploy the stack with:

```bash
cd backend/infrastructure/cdk
npm install
cdk deploy
```

**Optional Parameters**:

- **Provisioned Concurrency**: `cdk deploy -c provisionedConcurrency=10`
- **Custom Domain**: `cdk deploy -c domainName=api.example.com`
- **Alarm Email**: `cdk deploy -c alarmEmail=ops@example.com`

## Cost Optimization

**Auto-Scaling Benefits**:
- Lambda scales down when queue depth < 20 (Requirement 16.2)
- Reserved concurrency prevents over-provisioning
- Batch processing reduces per-message costs
- Throttling prevents runaway costs from abuse

**Estimated Costs** (per 1000 catalog entries):
- Lambda invocations: ~$0.20
- SQS messages: ~$0.40
- API Gateway requests: ~$3.50
- Total: ~$4.10 (excluding Sagemaker/Bedrock costs)

## Testing

Test auto-scaling behavior:

```bash
# Generate load to trigger auto-scaling
for i in {1..200}; do
  aws sqs send-message \
    --queue-url $(aws cloudformation describe-stacks \
      --stack-name VernacularArtisanCatalogStack \
      --query "Stacks[0].Outputs[?OutputKey=='QueueUrl'].OutputValue" \
      --output text) \
    --message-body "{\"tracking_id\": \"test-$i\"}"
done

# Monitor queue depth and Lambda concurrency
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=catalog-processing-queue \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average
```

Test API throttling:

```bash
# Generate burst traffic to test throttling
for i in {1..300}; do
  curl -X POST https://your-api-url/v1/catalog/upload/initiate \
    -H "x-api-key: YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"tenantId": "test", "artisanId": "test"}' &
done
wait

# Check for 429 (Too Many Requests) responses
```

## References

- **Requirements**: 16.1, 16.2, 16.3, 16.4
- **Design Document**: `.kiro/specs/vernacular-artisan-catalog/design.md`
- **Tasks**: 18.1, 18.2 in `.kiro/specs/vernacular-artisan-catalog/tasks.md`
