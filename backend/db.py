"""
Sento Analytics Builder — Config persistence
Uses DynamoDB when AWS credentials are set, falls back to local JSON file.
"""
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────
# DynamoDB backend
# ─────────────────────────────────────────────────────────

def _get_dynamo_table():
    """Return a boto3 DynamoDB Table resource, or None if not configured.

    Resolution order:
    1. DYNAMODB_ENDPOINT set → DynamoDB Local (dummy creds)
    2. TABLE_NAME set → real AWS DynamoDB via IAM role (Lambda) or env creds
    3. AWS_ACCESS_KEY_ID + SECRET set → real AWS DynamoDB with explicit creds
    4. Otherwise → None (local JSON fallback)
    """
    endpoint_url = os.getenv("DYNAMODB_ENDPOINT", "").strip() or None
    table_name = os.getenv("DYNAMO_TABLE", "").strip()
    region = os.getenv("AWS_REGION", "us-east-1").strip()
    # AWS_SESSION_TOKEN is set in Lambda (temp creds) — if present, let boto3
    # use the credential chain automatically instead of passing creds explicitly.
    session_token = os.getenv("AWS_SESSION_TOKEN", "").strip()
    key_id = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

    # Nothing configured → local fallback
    if not endpoint_url and not table_name:
        return None

    if not table_name:
        table_name = "sento-report-configs"

    try:
        import boto3
        kwargs: dict = dict(region_name=region)
        if endpoint_url:
            # DynamoDB Local: dummy creds required
            kwargs["endpoint_url"] = endpoint_url
            kwargs["aws_access_key_id"] = key_id or "local"
            kwargs["aws_secret_access_key"] = secret or "local"
        elif key_id and secret and not session_token:
            # Long-term explicit credentials (local dev → real AWS)
            kwargs["aws_access_key_id"] = key_id
            kwargs["aws_secret_access_key"] = secret
        # else: Lambda IAM role or any other boto3 credential chain
        ddb = boto3.resource("dynamodb", **kwargs)
        table = ddb.Table(table_name)
        return table
    except Exception as e:
        print(f"[db] DynamoDB not available: {e}. Using local fallback.")
        return None


_dynamo_table = _get_dynamo_table()


def _dynamo_available() -> bool:
    return _dynamo_table is not None


# ─────────────────────────────────────────────────────────
# Local JSON fallback
# ─────────────────────────────────────────────────────────

_LOCAL_FILE = Path(__file__).parent.parent / "configs.json"


def _load_local() -> dict:
    if _LOCAL_FILE.exists():
        try:
            return json.loads(_LOCAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_local(data: dict):
    _LOCAL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────

def list_configs() -> list[dict]:
    """Return all saved configs sorted by updated_at desc (without full component data)."""
    if _dynamo_available():
        resp = _dynamo_table.scan(
            ProjectionExpression="config_id, #n, created_at, updated_at, component_count",
            ExpressionAttributeNames={"#n": "name"},
        )
        items = resp.get("Items", [])
        # handle DynamoDB pagination
        while "LastEvaluatedKey" in resp:
            resp = _dynamo_table.scan(
                ProjectionExpression="config_id, #n, created_at, updated_at, component_count",
                ExpressionAttributeNames={"#n": "name"},
                ExclusiveStartKey=resp["LastEvaluatedKey"],
            )
            items.extend(resp.get("Items", []))
    else:
        data = _load_local()
        items = [
            {
                "config_id": v["config_id"],
                "name": v["name"],
                "created_at": v.get("created_at", ""),
                "updated_at": v.get("updated_at", ""),
                "component_count": v.get("component_count", 0),
            }
            for v in data.values()
        ]

    return sorted(items, key=lambda x: x.get("updated_at", ""), reverse=True)


def get_config(config_id: str) -> dict | None:
    """Return full config by id, or None if not found."""
    if _dynamo_available():
        resp = _dynamo_table.get_item(Key={"config_id": config_id})
        return resp.get("Item")
    else:
        data = _load_local()
        return data.get(config_id)


def save_config(name: str, config: dict, components: list, hist_rows: list) -> dict:
    """Create or update a named configuration. Returns the saved item."""
    config_id = str(uuid.uuid4())
    now = _now_iso()
    item = {
        "config_id": config_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "component_count": len(components),
        "config": config,
        "components": components,
        "hist_rows": hist_rows,
    }

    if _dynamo_available():
        _dynamo_table.put_item(Item=item)
    else:
        data = _load_local()
        data[config_id] = item
        _save_local(data)

    return item


def update_config(config_id: str, name: str, config: dict, components: list, hist_rows: list) -> dict | None:
    """Overwrite an existing config. Returns updated item or None if not found."""
    existing = get_config(config_id)
    if not existing:
        return None

    now = _now_iso()
    item = {
        **existing,
        "name": name,
        "updated_at": now,
        "component_count": len(components),
        "config": config,
        "components": components,
        "hist_rows": hist_rows,
    }

    if _dynamo_available():
        _dynamo_table.put_item(Item=item)
    else:
        data = _load_local()
        data[config_id] = item
        _save_local(data)

    return item


def delete_config(config_id: str) -> bool:
    """Delete a config. Returns True if deleted, False if not found."""
    if not get_config(config_id):
        return False

    if _dynamo_available():
        _dynamo_table.delete_item(Key={"config_id": config_id})
    else:
        data = _load_local()
        data.pop(config_id, None)
        _save_local(data)

    return True


def storage_backend() -> str:
    return "dynamodb" if _dynamo_available() else "local"
