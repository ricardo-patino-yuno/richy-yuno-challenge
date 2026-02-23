#!/bin/bash
# Demo script for Remessas Global Payment Screening API
# Shows all decision types: APPROVED, DENIED, REVIEW
#
# Prerequisites: Server running on port 8000
#   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

BASE="http://localhost:8000"

echo "============================================"
echo "  Remessas Global Payment Screening Demo"
echo "============================================"
echo ""

# ------------------------------------------------------------------
# 1. APPROVED -- Clean transaction
# A normal remittance from Mexico. No sanctions match, safe country,
# small amount, no velocity or structuring issues.
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  1. APPROVED - Clean transaction"
echo "--------------------------------------------"
echo "Sending $150 from Maria Garcia to Rosa Delgado in Mexico."
echo "Expected: APPROVED (no rules triggered)"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"Maria Garcia","recipient_name":"Rosa Delgado","amount":150.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-22T08:15:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 2. DENIED -- Exact sanctions match (sender)
# "Mohammad Ahmad" is on the sanctions list. Exact name match yields
# 100% similarity, which is above the 85% threshold.
# Score: 100 -> DENIED
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  2. DENIED - Exact sanctions match (sender)"
echo "--------------------------------------------"
echo "Sender 'Mohammad Ahmad' is on the sanctions list verbatim."
echo "Expected: DENIED with SANCTIONS_MATCH rule"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"Mohammad Ahmad","recipient_name":"Layla Khoury","amount":350.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:15:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 3. DENIED -- Fuzzy sanctions match (sender)
# "Muhammed Ahmad" is NOT on the sanctions list, but it fuzzy-matches
# "Mohammad Ahmad" / "Mohammed Ahmed" / "Muhammad Ahmad" above the
# 85% threshold. This demonstrates the fuzzy matching catching
# transliteration variants common in cross-border remittances.
# Score: 100 -> DENIED
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  3. DENIED - Fuzzy sanctions match (sender)"
echo "--------------------------------------------"
echo "Sender 'Muhammed Ahmad' is not literally on the list, but"
echo "fuzzy-matches 'Mohammad Ahmad' above the 85% threshold."
echo "Expected: DENIED with SANCTIONS_MATCH rule"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"Muhammed Ahmad","recipient_name":"Nour El-Din","amount":280.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T11:45:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 4. DENIED -- Sanctions match on RECIPIENT
# The sender is clean, but the recipient "Ali Hassan" is on the
# sanctions list. The system checks both sender and recipient names.
# Score: 100 -> DENIED
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  4. DENIED - Recipient sanctions match"
echo "--------------------------------------------"
echo "Sender 'Thomas Mueller' is clean, but recipient 'Ali Hassan'"
echo "is on the sanctions list. Both names are checked."
echo "Expected: DENIED with SANCTIONS_MATCH rule"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"Thomas Mueller","recipient_name":"Ali Hassan","amount":240.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T15:30:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 5. REVIEW -- High-risk country (Iran)
# Destination country "IR" (Iran) is in the high-risk jurisdictions
# list. The names are clean and the amount is small, but the
# destination alone triggers a REVIEW.
# Score: 50 -> REVIEW
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  5. REVIEW - High-risk country (Iran)"
echo "--------------------------------------------"
echo "Sending to Iran (IR), which is a high-risk jurisdiction."
echo "Expected: REVIEW with HIGH_RISK_COUNTRY rule"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"Nora Fischer","recipient_name":"Darius Tehrani","amount":250.00,"currency":"USD","destination_country":"IR","timestamp":"2026-02-22T09:15:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 6. REVIEW -- Large amount ($2,500)
# The transaction amount exceeds the $2,000 threshold. Names are
# clean and the destination (US) is safe, but the amount alone
# triggers a REVIEW for manual compliance check.
# Score: 50 -> REVIEW
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  6. REVIEW - Large amount ($2,500)"
echo "--------------------------------------------"
echo "Sending \$2,500 to a safe country with clean names."
echo "Expected: REVIEW with LARGE_AMOUNT rule (threshold: \$2,000)"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"William Chang","recipient_name":"Jessica Liu","amount":2500.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T09:45:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 7. REVIEW -- Velocity exceeded (>5 transactions/hour)
# Legitimate remittance customers send 1-2 transactions per week.
# Six transactions in under an hour is a red flag. We send 5
# transactions first (suppressed output), then the 6th triggers
# the velocity rule.
# Score: 50 -> REVIEW
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  7. REVIEW - Velocity exceeded (6th txn/hr)"
echo "--------------------------------------------"
echo "Sending 5 transactions first (output suppressed)..."
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"VelocityDemo","recipient_name":"Person A","amount":150.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:01:00Z"}' > /dev/null
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"VelocityDemo","recipient_name":"Person B","amount":250.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:05:00Z"}' > /dev/null
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"VelocityDemo","recipient_name":"Person C","amount":180.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:10:00Z"}' > /dev/null
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"VelocityDemo","recipient_name":"Person D","amount":320.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:15:00Z"}' > /dev/null
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"VelocityDemo","recipient_name":"Person E","amount":200.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:20:00Z"}' > /dev/null
echo "Now sending the 6th transaction (exceeds 5/hour threshold):"
echo "Expected: REVIEW with VELOCITY_EXCEEDED rule"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"VelocityDemo","recipient_name":"Person F","amount":330.00,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:25:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 8. REVIEW -- Structuring detected (3 x ~$500 in 30 min)
# Structuring is when someone splits a large transaction into
# smaller ones to evade reporting thresholds. Three transactions
# of similar amounts ($500, $490, $510 -- all within 20% variance)
# within 30 minutes triggers this rule.
# Score: 50 -> REVIEW
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  8. REVIEW - Structuring detected"
echo "--------------------------------------------"
echo "Sending 2 transactions of ~\$500 first (output suppressed)..."
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"StructDemo","recipient_name":"Recipient A","amount":500.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T16:00:00Z"}' > /dev/null
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"StructDemo","recipient_name":"Recipient B","amount":490.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T16:05:00Z"}' > /dev/null
echo "Now sending the 3rd similar-amount transaction (\$510):"
echo "Expected: REVIEW with STRUCTURING_DETECTED rule"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"StructDemo","recipient_name":"Recipient C","amount":510.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T16:10:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 9. Combined -- High-risk country + Large amount
# Multiple risk factors stack. Sending $3,000 to Iran triggers both
# HIGH_RISK_COUNTRY (50 pts) and LARGE_AMOUNT (50 pts) = score 100.
# Still REVIEW (not DENIED) because only sanctions matches cause
# DENIED decisions.
# Score: 100 -> REVIEW
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  9. REVIEW - Combined: country + amount"
echo "--------------------------------------------"
echo "Sending \$3,000 to Iran (IR). Two rules fire simultaneously:"
echo "HIGH_RISK_COUNTRY (50 pts) + LARGE_AMOUNT (50 pts) = 100."
echo "Expected: REVIEW (not DENIED -- only sanctions cause DENIED)"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"Henrik Dahl","recipient_name":"Majid Rahmani","amount":3000.00,"currency":"USD","destination_country":"IR","timestamp":"2026-02-22T11:00:00Z"}' | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 10. Configurable rules -- Change threshold, show effect
# First, show that $1,500 is APPROVED under the default $2,000
# threshold. Then lower the threshold to $1,000 via PUT /api/rules,
# and show that the same $1,500 amount now triggers REVIEW.
# Finally, restore the original threshold.
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  10. Configurable rules demo"
echo "--------------------------------------------"
echo "Step A: Send \$1,500 with default threshold (\$2,000)."
echo "Expected: APPROVED (1500 < 2000)"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"RuleDemo","recipient_name":"Someone","amount":1500.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T14:00:00Z"}' | python3 -m json.tool
echo ""
echo "Step B: Lower amount threshold from \$2,000 to \$1,000..."
curl -s -X PUT "$BASE/api/rules" -H "Content-Type: application/json" -d '{"velocity_threshold":5,"velocity_window_minutes":60,"amount_threshold":1000,"structuring_window_minutes":30,"structuring_min_count":3,"structuring_amount_variance":0.20,"fuzzy_match_threshold":85}' | python3 -m json.tool
echo ""
echo "Step C: Send \$1,500 again with new threshold (\$1,000)."
echo "Expected: REVIEW (1500 > 1000)"
echo ""
curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d '{"sender_name":"RuleDemo2","recipient_name":"Someone","amount":1500.00,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T14:05:00Z"}' | python3 -m json.tool
echo ""
echo "Step D: Restore default threshold (\$2,000)..."
curl -s -X PUT "$BASE/api/rules" -H "Content-Type: application/json" -d '{"velocity_threshold":5,"velocity_window_minutes":60,"amount_threshold":2000,"structuring_window_minutes":30,"structuring_min_count":3,"structuring_amount_variance":0.20,"fuzzy_match_threshold":85}' > /dev/null
echo "Threshold restored to \$2,000."
echo ""

# ------------------------------------------------------------------
# 11. Transaction history query
# Query all transactions for "VelocityDemo" from step 7 above.
# Should return 6 records (the 5 suppressed + 1 shown).
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  11. Transaction history query"
echo "--------------------------------------------"
echo "Querying transaction history for sender 'VelocityDemo':"
echo ""
curl -s "http://localhost:8000/api/transactions/VelocityDemo?hours=24" | python3 -m json.tool
echo ""

# ------------------------------------------------------------------
# 12. Audit trail query
# Query the full audit log filtered by a time range covering the
# demo transactions. Shows the complete request-to-decision trail
# that compliance officers would review.
# ------------------------------------------------------------------
echo "--------------------------------------------"
echo "  12. Audit trail query"
echo "--------------------------------------------"
echo "Querying audit trail for 2026-02-22 (showing first 3 entries):"
echo ""
curl -s "http://localhost:8000/api/audit?from_date=2026-02-22T00:00:00Z&to_date=2026-02-22T23:59:59Z" | python3 -c "import sys,json; entries=json.load(sys.stdin); print(json.dumps(entries[:3], indent=4)); print(f'\n... and {len(entries)-3} more entries' if len(entries)>3 else '')"
echo ""

echo "============================================"
echo "  Demo complete!"
echo "============================================"
