#!/usr/bin/env bash
# Deploy a single CloudFormation stack.
#
# Usage:
#   ./scripts/deploy-stack.sh <stack-path> <environment> <region>
#
# Example:
#   ./scripts/deploy-stack.sh report-generated/shared dev us-east-1
#   ./scripts/deploy-stack.sh report-generated/api dev us-east-1
#
# Stack name is derived from path: report-generated/shared -> report-generated-shared-dev
# Template resolution: tries $path.yaml first, then $path/template.yaml

set -euo pipefail

STACK_PATH="${1:?Usage: $0 <stack-path> <environment> <region>}"
ENVIRONMENT="${2:?}"
REGION="${3:?}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TEMPLATE="$ROOT_DIR/cfn-templates/$STACK_PATH.yaml"
if [[ ! -f "$TEMPLATE" ]]; then
    TEMPLATE="$ROOT_DIR/cfn-templates/$STACK_PATH/template.yaml"
fi

if [[ ! -f "$TEMPLATE" ]]; then
    echo "ERROR: Template not found for stack path: $STACK_PATH"
    echo "       Tried: cfn-templates/$STACK_PATH.yaml"
    echo "       Tried: cfn-templates/$STACK_PATH/template.yaml"
    exit 1
fi

# Derive stack name from path: report-generated/shared -> report-generated-shared-dev
STACK_NAME=$(echo "$STACK_PATH" | tr '/' '-')
STACK_NAME="${STACK_NAME}-${ENVIRONMENT}"

echo "    Stack name: $STACK_NAME"
echo "    Template:   $TEMPLATE"
echo "    Region:     $REGION"

# Build parameter overrides from params file
PARAM_OVERRIDES="Environment=$ENVIRONMENT Region=$REGION"

# Inject SSM SecureString params that CFN can't resolve via dynamic references
_resolve_secure() {
    local param_name=$1
    local ssm_path=$2
    if grep -q "$param_name" "$TEMPLATE" 2>/dev/null; then
        echo "    Resolving $param_name from SSM ($ssm_path)..."
        local value
        value=$(aws ssm get-parameter \
            --name "$ssm_path" \
            --with-decryption \
            --region "$REGION" \
            --query 'Parameter.Value' \
            --output text)
        PARAM_OVERRIDES="$PARAM_OVERRIDES $param_name=$value"
    fi
}

_resolve_secure "UbidotsToken" "/report-generated/${ENVIRONMENT}/ubidots/token"

# Check if this is a SAM template (has Transform: AWS::Serverless)
if grep -q "AWS::Serverless" "$TEMPLATE" 2>/dev/null; then
    echo "    Type: SAM template"
    sam build --template-file "$TEMPLATE" --build-dir "$ROOT_DIR/.aws-sam/build/$STACK_NAME" --base-dir "$ROOT_DIR"
    sam deploy \
        --template-file "$ROOT_DIR/.aws-sam/build/$STACK_NAME/template.yaml" \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --parameter-overrides $PARAM_OVERRIDES \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset \
        --no-confirm-changeset \
        --resolve-s3
else
    echo "    Type: CloudFormation template"
    aws cloudformation deploy \
        --template-file "$TEMPLATE" \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --parameter-overrides $PARAM_OVERRIDES \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset
fi

echo "    Done: $STACK_NAME"
