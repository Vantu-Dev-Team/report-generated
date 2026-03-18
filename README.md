# report-generated

FastAPI backend deployed to AWS Lambda via SAM. Powers a report builder app that proxies the Ubidots IoT API, persists report configurations in DynamoDB, and generates styled HTML reports from time-series data.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS + Bearer (Cognito)
┌─────────────────────────▼───────────────────────────────────┐
│          API Gateway (REST) — us-east-1                      │
│  Cognito Authorizer: us-east-1_OVlXl5RFG                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│     Lambda: us-east-1-report-generated-api-{env}            │
│     Runtime: Python 3.12 / FastAPI / Mangum                 │
│                                                              │
│   ┌──────────┐  ┌──────────┐  ┌────────────────────────┐   │
│   │ /configs │  │/generate │  │      /ubidots           │   │
│   │  (CRUD)  │  │ (HTML)   │  │ /devices, /variables    │   │
│   └────┬─────┘  └──────────┘  │ /data/values            │   │
│        │                      └───────────┬─────────────┘   │
└────────┼──────────────────────────────────┼─────────────────┘
         │                                  │
┌────────▼──────────┐            ┌──────────▼──────────────┐
│     DynamoDB      │            │   Ubidots Industrial API │
│ {region}-report-  │            │ industrial.api.ubidots   │
│ generated-data-   │            │       .com               │
│    {env}          │            └─────────────────────────-┘
└───────────────────┘
```

## Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| Framework | FastAPI + Mangum |
| Infra | AWS SAM (CloudFormation) |
| Database | DynamoDB (single-table) |
| Auth | AWS Cognito (Bearer token) |
| Secrets | AWS SSM Parameter Store |
| Logging | aws-lambda-powertools |
| HTTP client | httpx (async) |

## Prerequisites

- AWS CLI configured with appropriate credentials
- SAM CLI (`pip install aws-sam-cli`)
- Python 3.12

## Quick Start — Local Development

```bash
cd report-generated/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../../.env.example .env
# Edit .env with your values

uvicorn app:app --reload --port 8001
# Docs: http://localhost:8001/docs
```

## Deploy

### Pre-deploy: put SSM parameters

Before the first deploy, create these SSM parameters manually:

```bash
# Ubidots token (SecureString — resolved at deploy time, not by CFN)
aws ssm put-parameter \
  --name /report-generated/dev/ubidots/token \
  --type SecureString \
  --value "BBFF-your-token-here" \
  --region us-east-1

# Cognito User Pool ID (same pool as Nexus)
aws ssm put-parameter \
  --name /report-generated/dev/cognito/user-pool-id \
  --type String \
  --value "us-east-1_OVlXl5RFG" \
  --region us-east-1
```

### Phase 1 — Shared infrastructure (DynamoDB + SSM)

```bash
./scripts/deploy.sh dev us-east-1 phase1
```

Deploys stack: `report-generated-shared-dev`

Creates:
- DynamoDB table: `us-east-1-report-generated-data-dev`
- SSM: `/report-generated/dev/dynamodb/table-name`
- SSM: `/report-generated/dev/dynamodb/table-arn`

### Phase 2 — API (Lambda + API Gateway)

```bash
./scripts/deploy.sh dev us-east-1 phase2
```

Deploys stack: `report-generated-api-dev`

Creates:
- Lambda: `us-east-1-report-generated-api-dev`
- API Gateway: `us-east-1-report-generated-api-dev`
- Log group: `/aws/lambda/us-east-1-report-generated-api-dev`
- SSM: `/report-generated/dev/api/url`

### Deploy all phases

```bash
./scripts/deploy.sh dev us-east-1
```

### Verify deploy

```bash
./scripts/deploy.sh dev us-east-1 --verify
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ENVIRONMENT` | Deployment environment | `dev` |
| `TABLE_NAME` | DynamoDB table name | `us-east-1-report-generated-data-dev` |
| `UBIDOTS_TOKEN` | Ubidots API token | _(empty)_ |
| `AWS_REGION` | AWS region | `us-east-1` |
| `LOG_LEVEL` | Logging level | `INFO` |

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check |
| `GET` | `/docs` | None | Swagger UI |
| `GET` | `/configs` | Cognito | List all saved configurations |
| `GET` | `/configs/{id}` | Cognito | Get configuration by ID |
| `POST` | `/configs` | Cognito | Save a new configuration |
| `PUT` | `/configs/{id}` | Cognito | Update an existing configuration |
| `DELETE` | `/configs/{id}` | Cognito | Delete a configuration |
| `POST` | `/generate` | Cognito | Generate HTML report |
| `GET` | `/ubidots/devices` | Cognito | List Ubidots devices (paginated) |
| `GET` | `/ubidots/devices/{label}/variables` | Cognito | List variables for a device |
| `POST` | `/ubidots/data/values` | Cognito | Fetch raw variable values |

### Ubidots token override

All `/ubidots/*` endpoints accept an optional `X-Ubidots-Token` header to override the server-side token (useful for multi-tenant use).

## Resource Naming Convention

```
{region}-report-generated-{function}-{environment}
```

Examples:
- Lambda:   `us-east-1-report-generated-api-dev`
- DynamoDB: `us-east-1-report-generated-data-dev`
- Log group: `/aws/lambda/us-east-1-report-generated-api-dev`
- CFN stacks: `report-generated-shared-dev`, `report-generated-api-dev`

## SSM Parameter Paths

```
/report-generated/{env}/dynamodb/table-name
/report-generated/{env}/dynamodb/table-arn
/report-generated/{env}/cognito/user-pool-id   ← put manually before deploy
/report-generated/{env}/ubidots/token          ← put manually before deploy (SecureString)
/report-generated/{env}/api/url                ← created by api stack
```

## Cognito

Uses the same Cognito User Pool as Nexus:

- Pool ID: `us-east-1_OVlXl5RFG`
- Client ID: `3jghasft3af5uv5eukosn950pf`

The pool ID is read from SSM (`/report-generated/{env}/cognito/user-pool-id`) at deploy time, so it must exist before running Phase 2.

## DynamoDB Data Model

Single-table design:

| Attribute | Type | Description |
|---|---|---|
| `PK` | String | `config_id` (UUID) |
| `SK` | String | `#REPORT_CONFIG` (fixed) |
| `config_id` | String | UUID of the config |
| `name` | String | Human-readable name |
| `config` | Map | Report header config (title, dates, etc.) |
| `components` | List | Ordered list of report components |
| `hist_rows` | List | Historical data rows |
| `component_count` | Number | Cached count of components |
| `created_at` | String | ISO 8601 UTC timestamp |
| `updated_at` | String | ISO 8601 UTC timestamp |
