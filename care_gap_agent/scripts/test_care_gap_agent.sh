#!/usr/bin/env bash
# test_care_gap_agent.sh — end-to-end smoke test for the care_gap_agent.
#
# Exercises the full request pipeline:
#   API key check → A2A metadata → FHIR hook → ADK tool → MCP HTTP call → MCP tool.
#
# Usage:
#   ./scripts/test_care_gap_agent.sh                         # http://127.0.0.1:8001
#   ./scripts/test_care_gap_agent.sh http://my-host:8001
#   API_KEY=demo-key FHIR_URL=https://r4.smarthealthit.org \
#     PATIENT_ID=87a339d0-8cae-418e-89c7-8651e6aab3c6 ./scripts/test_care_gap_agent.sh
#
# Run the agent + MCP server first:
#   (terminal 1)  cd ../care_gap_mcp && uv run python main.py
#   (terminal 2)  uvicorn care_gap_agent.app:a2a_app --host 127.0.0.1 --port 8001 --log-level info
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8001}"
RPC_URL="${BASE_URL%/}/"
API_KEY="${API_KEY:-demo-key}"
FHIR_URL="${FHIR_URL:-https://r4.smarthealthit.org}"
FHIR_TOKEN="${FHIR_TOKEN:-public-sandbox-no-token}"
PATIENT_ID="${PATIENT_ID:-87a339d0-8cae-418e-89c7-8651e6aab3c6}"
PO_BASE="${PO_PLATFORM_BASE_URL:-https://app.promptopinion.ai}"

post_json() {
  local label="$1"
  local payload="$2"
  echo
  echo "===== ${label} ====="
  curl -sS -i -X POST "$RPC_URL" \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: ${API_KEY}" \
    --data "$payload"
  echo
}

read -r -d '' PAYLOAD_FIND_GAPS <<JSON || true
{
  "jsonrpc": "2.0",
  "id": "find-gaps",
  "method": "message/send",
  "params": {
    "metadata": {
      "${PO_BASE}/schemas/a2a/v1/fhir-context": {
        "fhirUrl": "${FHIR_URL}",
        "fhirToken": "${FHIR_TOKEN}",
        "patientId": "${PATIENT_ID}"
      }
    },
    "message": {
      "kind": "message",
      "message_id": "msg-find-gaps",
      "role": "user",
      "parts": [{"kind": "text", "text": "What preventive care gaps does this patient have?"}]
    }
  }
}
JSON

read -r -d '' PAYLOAD_DRAFT <<JSON || true
{
  "jsonrpc": "2.0",
  "id": "draft",
  "method": "message/send",
  "params": {
    "metadata": {
      "${PO_BASE}/schemas/a2a/v1/fhir-context": {
        "fhirUrl": "${FHIR_URL}",
        "fhirToken": "${FHIR_TOKEN}",
        "patientId": "${PATIENT_ID}"
      }
    },
    "message": {
      "kind": "message",
      "message_id": "msg-draft",
      "role": "user",
      "parts": [{"kind": "text", "text": "Draft an SMS to the patient about the most urgent gap."}]
    }
  }
}
JSON

echo "Target: $RPC_URL"
echo "FHIR:   $FHIR_URL  patient=$PATIENT_ID"

post_json "Find care gaps" "$PAYLOAD_FIND_GAPS"
post_json "Draft outreach" "$PAYLOAD_DRAFT"
