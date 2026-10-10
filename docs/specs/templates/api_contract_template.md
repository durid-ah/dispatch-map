# API Contract Specification: [Endpoint / Resource Name]

- **Status**: Draft | Active | Deprecated
- **Resource**: `[e.g. /events]`
- **Target Router**: `packages/api/routers/[name].py`

---

## 1. Overview
[Brief description of what this API contract exposes and who consumes it.]

---

## 2. Endpoints

### `[METHOD] /path`

#### Summary
[Short description of endpoint purpose]

#### Security / Authentication
- None (Public) | API Key | JWT Bearer

#### Query Parameters
| Parameter | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `hours` | `integer` | No | `24` | `ge=1, le=168` | Lookback window in hours |

#### Request Body
- Content-Type: `application/json`
```json
{
  "field": "value"
}
```

#### Responses

##### `200 OK`
```json
[
  {
    "id": 1,
    "call_type": "MEDICAL EMERGENCY",
    "latitude": 37.54,
    "longitude": -77.43
  }
]
```

##### `422 Unprocessable Entity`
- Standard FastAPI validation error schema.

---

## 3. Pydantic Schemas

```python
# Exact Python models defining request and response
from pydantic import BaseModel

class RequestPayload(BaseModel):
    ...

class ResponsePayload(BaseModel):
    ...
```

---

## 4. Contract Sync & Testing Plan
1. Export contract: `./run-dev.sh spec:export`
2. Sync TypeScript: `./run-dev.sh spec:types`
3. Verify test client: `uv run python -m unittest packages/api/tests/test_api.py`
