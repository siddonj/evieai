#!/usr/bin/env bash
# Seed demo document workflows into the Azure dev orchestrator.
# The orchestrator's workflow DB is on ephemeral storage, so this must be
# re-run every time the container apps are restarted.
# Usage: scripts/seed_demo_workflows.sh
set -euo pipefail

BASE="${ORCHESTRATOR_URL:-https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io}"
USER_ID="admin@evieai.local"

create() {
  curl -sf --max-time 30 -X POST "$BASE/document-actions/draft" \
    -H 'Content-Type: application/json' \
    -d "$1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
}

# 1. Executive Briefing — taken all the way to executed + export
ID1=$(create '{
  "user_id": "admin@evieai.local",
  "work_packet_id": "wp-portfolio-q2",
  "document_type": "executive_briefing",
  "title": "Q2 Portfolio Performance Briefing",
  "source_summary": "Portfolio occupancy held at 94.2% across 12 sites, up 1.1 points quarter-over-quarter. Net operating income reached $4.8M against a $4.6M target, driven by renewals at Riverside Commons and Cedar Point. Delinquency fell to 2.3%. Two sites (Oakview Terrace, Marina Landing) remain below the 90% occupancy threshold and have remediation plans in flight. Maintenance backlog cleared 68% of open work orders, with HVAC replacements at Cedar Point scheduled for August."
}')
echo "created executive briefing id=$ID1"
curl -sf --max-time 30 -X POST "$BASE/document-actions/$ID1/approve" \
  -H 'Content-Type: application/json' \
  -d '{"destination_type":"onedrive","destination_ref":"Reports/Executive/Q2-2026","output_formats":["pdf","docx"]}' > /dev/null
echo "approved id=$ID1"
curl -sf --max-time 90 -X POST "$BASE/document-actions/$ID1/finalize" > /dev/null
echo "finalized id=$ID1"
curl -sf --max-time 90 -X POST "$BASE/document-actions/$ID1/export-package" > /dev/null
echo "exported id=$ID1"

# 2. Board Report — approved, awaiting finalize
ID2=$(create '{
  "user_id": "admin@evieai.local",
  "work_packet_id": "wp-board-june",
  "document_type": "board_report",
  "title": "July Board Report — Asset Overview",
  "source_summary": "Monthly board packet covering the 12-property portfolio: rent roll summary, capital projects status, and variance analysis. Capital spend is tracking 8% under budget year-to-date. The Marina Landing repositioning is 60% complete and on schedule for a September lease-up. Insurance renewals were locked at a 4% increase versus the 11% market average. Recommended actions: approve the Cedar Point HVAC capital release and review the Oakview Terrace concession strategy."
}')
echo "created board report id=$ID2"
curl -sf --max-time 30 -X POST "$BASE/document-actions/$ID2/approve" \
  -H 'Content-Type: application/json' \
  -d '{"destination_type":"email","destination_ref":"board@evieai.local","output_formats":["pdf"]}' > /dev/null
echo "approved id=$ID2"

# 3. Operational Report — fresh draft
ID3=$(create '{
  "user_id": "admin@evieai.local",
  "work_packet_id": "wp-ops-weekly",
  "document_type": "operational_report",
  "title": "Weekly Operations Summary — Sites & Work Orders",
  "source_summary": "Across all sites this week: 142 work orders opened, 128 closed (90% same-week resolution). Average response time 6.4 hours, beating the 8-hour SLA. Three escalations: a water intrusion event at Riverside Commons (contained, remediation vendor on site), elevator modernization permits approved at Marina Landing, and a staffing gap at Oakview Terrace with two maintenance roles now posted. Leasing traffic up 12% week-over-week with 38 tours scheduled."
}')
echo "created operational report id=$ID3 (left as draft)"

echo "--- final state ---"
curl -sf --max-time 20 "$BASE/document-actions?limit=10&user_id=$USER_ID" \
  | python3 -c 'import json,sys; [print(f"  #{i[\"id\"]:>2}  {i[\"status\"]:<9}  {i[\"title\"]}") for i in json.load(sys.stdin)["items"]]'
