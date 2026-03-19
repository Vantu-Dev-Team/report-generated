#!/usr/bin/env bash
# deploy.sh — Despliega sento-builder (Lambda + API Gateway + DynamoDB) con SAM
#
# Uso:
#   ./deploy.sh                        # dev, us-east-1
#   ./deploy.sh prod                   # prod, us-east-1
#   ./deploy.sh dev us-east-1
#   ./deploy.sh dev us-east-1 BBFF-... # con token de Ubidots explícito

set -euo pipefail

ENVIRONMENT="${1:-dev}"
REGION="${2:-us-east-1}"
UBIDOTS_TOKEN="${3:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_NAME="sento-builder-${ENVIRONMENT}"
BUILD_DIR="$ROOT/.aws-sam/build"

# Leer token del .env si no se pasó como argumento
if [[ -z "$UBIDOTS_TOKEN" && -f "$ROOT/.env" ]]; then
    UBIDOTS_TOKEN=$(grep -E '^UBIDOTS_TOKEN=' "$ROOT/.env" | cut -d= -f2- | tr -d '"' || true)
fi

echo "=== sento-builder deploy ==="
echo "Stack:       $STACK_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region:      $REGION"
echo "Token:       ${UBIDOTS_TOKEN:+****** (set)}"
echo ""

# Build
echo "--- SAM build ---"
sam build \
    --template-file "$ROOT/template.yaml" \
    --build-dir "$BUILD_DIR/$STACK_NAME" \
    --base-dir "$ROOT" \
    --region "$REGION"

echo ""
echo "--- SAM deploy ---"
PARAM_OVERRIDES="Environment=$ENVIRONMENT"
[[ -n "$UBIDOTS_TOKEN" ]] && PARAM_OVERRIDES="$PARAM_OVERRIDES UbidotsToken=$UBIDOTS_TOKEN"

sam deploy \
    --template-file "$BUILD_DIR/$STACK_NAME/template.yaml" \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --parameter-overrides $PARAM_OVERRIDES \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --no-confirm-changeset \
    --resolve-s3

echo ""
echo "=== Deploy completo ==="
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text)
echo "API URL: $API_URL"
echo ""
echo "Prueba: curl $API_URL/api/configs"
