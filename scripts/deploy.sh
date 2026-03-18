#!/usr/bin/env bash
# Master deploy script: deploys CFN stacks in dependency order, by phase.
#
# Usage:
#   ./scripts/deploy.sh <environment> [region] [phase|stack-filter]
#
# Deploy everything:
#   ./scripts/deploy.sh dev                              # All phases, us-east-1
#   ./scripts/deploy.sh prod us-east-1                  # All phases, explicit region
#
# Deploy by phase:
#   ./scripts/deploy.sh dev us-east-1 phase1             # Shared infra only
#   ./scripts/deploy.sh dev us-east-1 phase2             # API only
#
# Deploy a single stack:
#   ./scripts/deploy.sh dev us-east-1 report-generated/shared
#   ./scripts/deploy.sh dev us-east-1 report-generated/api
#
# Verify after deploy:
#   ./scripts/deploy.sh dev us-east-1 phase1 --verify    # Deploy + verify phase 1
#   ./scripts/deploy.sh dev us-east-1 --verify           # Deploy all + verify each phase
#
# Deploy order:
#   Phase 1: report-generated/shared  — DynamoDB table + SSM params
#   Phase 2: report-generated/api     — Lambda + API Gateway + Cognito auth

set -euo pipefail

ENVIRONMENT="${1:?Usage: $0 <environment> [region] [phase|stack-filter] [--verify]}"
REGION="${2:-us-east-1}"
FILTER="${3:-}"
VERIFY="${4:-}"

# Also check if --verify is in position 3
if [[ "$FILTER" == "--verify" ]]; then
    VERIFY="--verify"
    FILTER=""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== report-generated Deploy ==="
echo "Environment: $ENVIRONMENT"
echo "Region:      $REGION"
echo "Filter:      ${FILTER:-all}"
echo "Verify:      ${VERIFY:-no}"
echo ""

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|stage|prod)$ ]]; then
    echo "ERROR: Environment must be dev, stage, or prod"
    exit 1
fi

# Auto-detect and validate AWS account
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID:  $ACCOUNT_ID"
echo ""

# ---------------------------------------------------------------------------
# Stack definitions by phase
# ---------------------------------------------------------------------------

# Phase 1: Shared — DynamoDB table and SSM parameters
PHASE1=(
    "report-generated/shared"
)

# Phase 2: API — Lambda + API Gateway with Cognito auth (depends on Phase 1)
PHASE2=(
    "report-generated/api"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

deploy_phase() {
    local phase_name="$1"
    shift
    local stacks=("$@")

    echo "--- $phase_name ---"
    local deployed=0
    for stack in "${stacks[@]}"; do
        # Apply filter (skip phase filters here, handled by caller)
        if [[ -n "$FILTER" && "$FILTER" != phase* && "$stack" != *"$FILTER"* ]]; then
            echo "  SKIP: $stack (filtered)"
            continue
        fi

        template="$ROOT_DIR/cfn-templates/$stack.yaml"
        if [[ ! -f "$template" ]]; then
            template="$ROOT_DIR/cfn-templates/$stack/template.yaml"
        fi
        if [[ ! -f "$template" ]]; then
            echo "  SKIP: $stack (template not found yet)"
            continue
        fi

        echo "  DEPLOY: $stack"
        "$SCRIPT_DIR/deploy-stack.sh" "$stack" "$ENVIRONMENT" "$REGION"
        deployed=$((deployed + 1))
    done

    if [[ $deployed -eq 0 ]]; then
        echo "  (no stacks deployed in this phase)"
    fi
    echo ""
}

verify_phase1() {
    echo "--- Verify Phase 1: Shared Infrastructure ---"
    echo ""
    echo "  Check DynamoDB table:"
    echo "    aws dynamodb describe-table \\"
    echo "      --table-name $REGION-report-generated-data-$ENVIRONMENT \\"
    echo "      --region $REGION \\"
    echo "      --query 'Table.{Name:TableName,Status:TableStatus,ItemCount:ItemCount}'"
    echo ""
    echo "  Check SSM params published:"
    echo "    aws ssm get-parameters-by-path \\"
    echo "      --path /report-generated/$ENVIRONMENT/ \\"
    echo "      --region $REGION \\"
    echo "      --query 'Parameters[].Name'"
    echo ""
    echo "  Check CFN stack status:"
    echo "    aws cloudformation describe-stacks \\"
    echo "      --stack-name report-generated-shared-$ENVIRONMENT \\"
    echo "      --region $REGION \\"
    echo "      --query 'Stacks[0].StackStatus'"
    echo ""
}

verify_phase2() {
    echo "--- Verify Phase 2: API ---"
    echo ""
    echo "  Get API URL from SSM:"
    echo "    API_URL=\$(aws ssm get-parameter \\"
    echo "      --name /report-generated/$ENVIRONMENT/api/url \\"
    echo "      --region $REGION \\"
    echo "      --query Parameter.Value --output text)"
    echo ""
    echo "  Check API health:"
    echo "    curl -s \$API_URL/health | jq ."
    echo ""
    echo "  Check Lambda function:"
    echo "    aws lambda get-function \\"
    echo "      --function-name $REGION-report-generated-api-$ENVIRONMENT \\"
    echo "      --region $REGION \\"
    echo "      --query 'Configuration.{State:State,Runtime:Runtime,MemorySize:MemorySize}'"
    echo ""
    echo "  Check CFN stack status:"
    echo "    aws cloudformation describe-stacks \\"
    echo "      --stack-name report-generated-api-$ENVIRONMENT \\"
    echo "      --region $REGION \\"
    echo "      --query 'Stacks[0].StackStatus'"
    echo ""
}

# ---------------------------------------------------------------------------
# Deploy by phase
# ---------------------------------------------------------------------------

should_run_phase() {
    local phase="$1"
    # No filter = run all
    [[ -z "$FILTER" ]] && return 0
    # Exact phase match
    [[ "$FILTER" == "$phase" ]] && return 0
    # Project/stack filter (not a phase keyword) = run all phases, filter inside
    [[ "$FILTER" != phase* ]] && return 0
    return 1
}

if should_run_phase "phase1"; then
    deploy_phase "Phase 1 - Shared Infrastructure" "${PHASE1[@]}"
    [[ "$VERIFY" == "--verify" ]] && verify_phase1
fi

if should_run_phase "phase2"; then
    deploy_phase "Phase 2 - API" "${PHASE2[@]}"
    [[ "$VERIFY" == "--verify" ]] && verify_phase2
fi

echo "=== Deploy complete ==="
