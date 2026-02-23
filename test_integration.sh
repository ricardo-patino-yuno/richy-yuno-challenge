#!/bin/bash
# Integration test script for Remessas Global Payment Screening API

BASE="http://localhost:8000"
PASS=0
FAIL=0

check() {
    local test_name="$1"
    local expected_decision="$2"
    local response="$3"
    local actual=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['decision'])" 2>/dev/null)
    if [ "$actual" = "$expected_decision" ]; then
        echo "PASS: $test_name → $actual"
        PASS=$((PASS+1))
    else
        echo "FAIL: $test_name → expected $expected_decision, got $actual"
        echo "  Response: $response"
        FAIL=$((FAIL+1))
    fi
}

post() {
    curl -s -X POST "$BASE/api/screening" -H "Content-Type: application/json" -d "$1"
}

sleep 2

echo "===== INTEGRATION TESTS ====="
echo ""

# TEST 1: Clean transaction
R=$(post '{"sender_name":"Maria Garcia","recipient_name":"Rosa Delgado","amount":150,"currency":"USD","destination_country":"MX","timestamp":"2026-02-22T08:15:00Z"}')
check "Clean transaction" "APPROVED" "$R"

# TEST 2: Sanctions exact match (sender)
R=$(post '{"sender_name":"Mohammad Ahmad","recipient_name":"Layla Khoury","amount":350,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:15:00Z"}')
check "Sanctions exact (sender)" "DENIED" "$R"

# TEST 3: Sanctions fuzzy match (sender)
R=$(post '{"sender_name":"Muhammed Ahmad","recipient_name":"Nour El-Din","amount":280,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T11:45:00Z"}')
check "Sanctions fuzzy (sender)" "DENIED" "$R"

# TEST 4: Sanctions match (recipient)
R=$(post '{"sender_name":"Thomas Mueller","recipient_name":"Ali Hassan","amount":240,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T15:30:00Z"}')
check "Sanctions match (recipient)" "DENIED" "$R"

# TEST 5: High-risk country
R=$(post '{"sender_name":"Nora Fischer","recipient_name":"Darius Tehrani","amount":250,"currency":"USD","destination_country":"IR","timestamp":"2026-02-22T09:15:00Z"}')
check "High-risk country (IR)" "REVIEW" "$R"

# TEST 6: Large amount
R=$(post '{"sender_name":"William Chang","recipient_name":"Jessica Liu","amount":2500,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T09:45:00Z"}')
check "Large amount (2500)" "REVIEW" "$R"

# TEST 7: Velocity — send 5 transactions, then 6th should trigger
for i in 1 2 3 4 5; do
    post "{\"sender_name\":\"VelocityTest\",\"recipient_name\":\"Person $i\",\"amount\":${i}50,\"currency\":\"USD\",\"destination_country\":\"MX\",\"timestamp\":\"2026-02-23T12:0${i}:00Z\"}" > /dev/null
done
R=$(post '{"sender_name":"VelocityTest","recipient_name":"Person 6","amount":330,"currency":"USD","destination_country":"MX","timestamp":"2026-02-23T12:35:00Z"}')
check "Velocity (6th txn)" "REVIEW" "$R"

# TEST 8: Structuring — 3 similar amounts in 30 min
post '{"sender_name":"StructTest","recipient_name":"A","amount":500,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T16:00:00Z"}' > /dev/null
post '{"sender_name":"StructTest","recipient_name":"B","amount":490,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T16:05:00Z"}' > /dev/null
R=$(post '{"sender_name":"StructTest","recipient_name":"C","amount":510,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T16:10:00Z"}')
check "Structuring (3x ~500)" "REVIEW" "$R"

# TEST 9: High-risk country + large amount (combined)
R=$(post '{"sender_name":"Henrik Dahl","recipient_name":"Majid Rahmani","amount":3000,"currency":"USD","destination_country":"IR","timestamp":"2026-02-22T11:00:00Z"}')
check "Country + Amount combo" "REVIEW" "$R"

# TEST 10: Transaction history query
HISTORY=$(curl -s "$BASE/api/transactions/VelocityTest?hours=24")
COUNT=$(echo "$HISTORY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ "$COUNT" = "6" ]; then
    echo "PASS: Transaction history (6 records)"
    PASS=$((PASS+1))
else
    echo "FAIL: Transaction history — expected 6, got $COUNT"
    FAIL=$((FAIL+1))
fi

# TEST 11: Batch screening
BATCH_R=$(curl -s -X POST "$BASE/api/screening/batch" -H "Content-Type: application/json" -d '{"transactions":[{"sender_name":"Clean Person","recipient_name":"Other","amount":100,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:00:00Z"},{"sender_name":"Omar Farooq","recipient_name":"Test","amount":200,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:00:00Z"},{"sender_name":"Safe Person","recipient_name":"Friend","amount":300,"currency":"USD","destination_country":"IR","timestamp":"2026-02-22T10:00:00Z"}]}')
BATCH_OK=$(echo "$BATCH_R" | python3 -c "
import sys,json
d=json.load(sys.stdin)
s=d['summary']
ok = s['total']==3 and s['approved']>=1 and s['denied']>=1 and s['review']>=1
print('yes' if ok else 'no')
" 2>/dev/null)
if [ "$BATCH_OK" = "yes" ]; then
    echo "PASS: Batch screening (3 txns, mixed decisions)"
    PASS=$((PASS+1))
else
    echo "FAIL: Batch screening"
    echo "  Response: $BATCH_R"
    FAIL=$((FAIL+1))
fi

# TEST 12: Rules config GET
RULES=$(curl -s "$BASE/api/rules")
HAS_THRESH=$(echo "$RULES" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('velocity_threshold')==5 else 'no')" 2>/dev/null)
if [ "$HAS_THRESH" = "yes" ]; then
    echo "PASS: GET /api/rules"
    PASS=$((PASS+1))
else
    echo "FAIL: GET /api/rules"
    FAIL=$((FAIL+1))
fi

# TEST 13: Rules config PUT (change amount threshold)
curl -s -X PUT "$BASE/api/rules" -H "Content-Type: application/json" -d '{"velocity_threshold":5,"velocity_window_minutes":60,"amount_threshold":1000,"structuring_window_minutes":30,"structuring_min_count":3,"structuring_amount_variance":0.20,"fuzzy_match_threshold":85}' > /dev/null
R=$(post '{"sender_name":"RuleTest","recipient_name":"Someone","amount":1500,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:00:00Z"}')
check "Rules update (threshold 1000, amt 1500)" "REVIEW" "$R"
# Restore
curl -s -X PUT "$BASE/api/rules" -H "Content-Type: application/json" -d '{"velocity_threshold":5,"velocity_window_minutes":60,"amount_threshold":2000,"structuring_window_minutes":30,"structuring_min_count":3,"structuring_amount_variance":0.20,"fuzzy_match_threshold":85}' > /dev/null

# TEST 14: Audit trail
AUDIT=$(curl -s "$BASE/api/audit")
AUDIT_COUNT=$(echo "$AUDIT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ "$AUDIT_COUNT" -gt "0" ] 2>/dev/null; then
    echo "PASS: Audit trail ($AUDIT_COUNT entries)"
    PASS=$((PASS+1))
else
    echo "FAIL: Audit trail"
    FAIL=$((FAIL+1))
fi

# TEST 15: Health endpoint
HEALTH=$(curl -s "$BASE/health")
if echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='healthy'" 2>/dev/null; then
    echo "PASS: Health endpoint"
    PASS=$((PASS+1))
else
    echo "FAIL: Health endpoint"
    FAIL=$((FAIL+1))
fi

echo ""
echo "===== RESULTS: $PASS passed, $FAIL failed ====="
