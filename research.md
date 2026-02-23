# Research: Remessas Global Payment Screening API

## Challenge Overview

- **Title**: "The Compliance Nightmare: Build Remessas Global's Payment Screening API"
- **Category**: Backend
- **Time Limit**: 120 minutes (deadline: Feb 23, 2026 6:15 PM UTC)
- **Candidate**: Ricardo Patino

Build a REST API that performs real-time transaction screening for a cross-border remittance platform. The fictional client "Remessas Global" processes thousands of daily transactions across 40+ countries (Latin America, Africa, Southeast Asia), typically $50-$500 USD each. Their banking partner issued a compliance violation — they need automated screening or lose the banking relationship.

---

## Compliance Domain Concepts

| Concept | What It Means |
|---------|---------------|
| **Sanctions Lists** | Government lists (OFAC, UN, EU) of prohibited individuals/organizations/countries. Transactions involving sanctioned entities must be DENIED. |
| **High-Risk Jurisdictions** | Countries with weak financial oversight. Not blocked outright, but require extra scrutiny (flag for REVIEW). |
| **Transaction Velocity** | Detecting unusual frequency — e.g., >5 transactions/hour from same sender is suspicious. |
| **PEPs** | Politically Exposed Persons — government officials, politicians, family members. Require enhanced due diligence. |
| **Structuring** | Breaking large amounts into multiple smaller transactions to evade reporting thresholds. Illegal. Example: 5 x $500 in 30 minutes instead of 1 x $2,500. |

---

## Functional Requirements

### Requirement 1: Transaction Screening Endpoint

**Input fields:**
- `sender_name` — Name of the person sending money
- `recipient_name` — Name of the person receiving money
- `amount` — Transaction amount
- `currency` — Currency code
- `destination_country` — ISO country code of destination
- `timestamp` — When the transaction occurs

**Output fields:**
- `decision` — One of: `APPROVED`, `DENIED`, `REVIEW`
- `risk_score` — Integer 0-100
- `reasons` — Array of human-readable strings explaining the decision
- `matched_rules` — Array of specific compliance rules that triggered

**Screening checks to implement (in order of severity):**

1. **Sanctions Matching** — Check sender and recipient names against sanctions list. Must support fuzzy matching (name variants like "Mohammad Ahmad" / "Mohammed Ahmed"). Match = DENIED.
2. **High-Risk Country Flagging** — If destination country is in the high-risk list, flag for REVIEW and increase risk score.
3. **Transaction Velocity** — If sender has >5 transactions in the last hour, flag. Requires historical data lookup.
4. **Large Transaction Amounts** — Amounts > $2,000 USD equivalent get flagged.
5. **Structuring Detection** — Multiple similar-sized transactions from same sender within a short timeframe (e.g., 5 x $500 in 30 minutes).

### Requirement 2: Historical Transaction Analysis

- **Store transactions** — In-memory, file-based, or DB (all acceptable).
- **Query history** — Ability to look up a customer's transaction history (e.g., last 24 hours).
- **Feed into screening** — Velocity and structuring detection must use historical data.
- **Risk score adjustment** — Customer patterns should influence scoring.

---

## Decision Logic (My Analysis)

Based on the requirements, here's how decisions should flow:

```
IF sanctions match (sender OR recipient) → DENIED (risk_score near 100)
ELSE IF structuring detected → REVIEW (risk_score 60-80)
ELSE IF velocity threshold exceeded → REVIEW (risk_score 50-70)
ELSE IF high-risk country + large amount → REVIEW (risk_score 40-60)
ELSE IF high-risk country OR large amount → REVIEW (risk_score 20-40)
ELSE → APPROVED (risk_score 0-20)
```

Risk score should be cumulative — multiple flags stack. If it crosses a threshold (e.g., 60+), decision becomes REVIEW. If sanctions hit, always DENIED.

---

## Stretch Goals (Optional, 5 points)

### A: Batch Screening
- Accept array of 10-1,000 transactions
- Return individual results + summary report (counts of APPROVED/DENIED/REVIEW, common risk factors)

### B: Configurable Rules Engine
- Rules loaded from config file or modifiable via API
- Thresholds, sanctions lists, country lists can be updated without code changes
- Demonstrate at least one dynamic rule modification

### C: Audit Trail
- Log every screening decision with: timestamp, request details, decision, reasons
- Retrieval endpoint to query by transaction ID or time range
- Critical for regulatory audits

---

## Test Data Requirements

Must provide:

### 1. Sanctions List (20-30 entries)
- Individual names with spelling variations (fuzzy matching test cases)
- Organization names
- Examples: "Mohammad Ahmad" / "Mohammed Ahmed" (should both match)

### 2. High-Risk Countries (8-12 entries)
- Mix of real-world high-risk jurisdictions
- Suggested: Iran, North Korea, Syria, Myanmar, Yemen, Libya, Somalia, South Sudan, Afghanistan, Iraq, Venezuela, Cuba

### 3. Transaction Dataset (100-150 transactions)
- 20+ unique customer IDs
- Various destination countries (mix of high-risk and normal)
- Amount range: $50-$5,000 USD
- Multi-transaction customers for velocity testing
- 24+ hour timestamp span
- Must include explicit examples of:
  - DENIED outcomes (sanctions matches)
  - REVIEW outcomes (various risk factors)
  - APPROVED outcomes (clean transactions)
  - Structuring patterns (e.g., 5 x $500 in 30 minutes from same sender)

---

## Evaluation Rubric

| Criterion | Points | Notes |
|-----------|--------|-------|
| Core functionality | 25 | Decisions + risk scores + reasoning working |
| Compliance logic accuracy | 25 | All rule types correctly implemented |
| Historical tracking | 15 | Storage + querying + feeding into decisions |
| Code quality | 10 | Clean, organized, well-structured |
| Test data comprehensiveness | 10 | Covers all edge cases |
| Documentation | 10 | README with setup, testing, architecture |
| Stretch goals | 5 | Any of A/B/C implemented |
| **Total** | **100** | |

**Key insight**: Core functionality + compliance logic = 50 points (half the grade). These must be rock solid.

---

## Technical Decisions to Make

### Language/Framework
- Free choice. Given the 90-minute target for core requirements, we need something fast to develop in.
- **Recommendation**: Go with Gin, or Node.js/TypeScript with Express, or Python with FastAPI.
- FastAPI is probably fastest to prototype: built-in validation, auto docs, async support.

### Data Storage
- In-memory is explicitly acceptable and simplest for the time constraint.
- A simple map/dictionary keyed by sender_name or customer_id storing transaction history.

### Fuzzy Matching Strategy
- Exact matching is acceptable per the challenge.
- Fuzzy matching (Levenshtein distance, phonetic algorithms like Soundex/Metaphone) is an enhancement.
- Levenshtein with a threshold (e.g., distance <= 2) would catch "Mohammad"/"Mohammed" variants.
- String normalization: lowercase, remove special chars, trim whitespace.

### Architecture
- Single service, REST API
- In-memory store for transactions and reference data
- Load sanctions list and high-risk countries from JSON/config files at startup

---

## API Endpoints (Planned)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/screening` | Screen a single transaction |
| POST | `/api/screening/batch` | Batch screen (stretch goal A) |
| GET | `/api/transactions/{customer_id}` | Get customer transaction history |
| GET | `/api/transactions` | Query transactions by time range |
| GET | `/api/audit` | Audit trail (stretch goal C) |
| PUT | `/api/rules` | Update rules (stretch goal B) |
| GET | `/api/rules` | Get current rules config |
| GET | `/api/health` | Health check |

---

## Time Budget (90 minutes)

| Phase | Time | What |
|-------|------|------|
| 1. Project setup + data files | 10 min | Scaffold project, create sanctions list, countries, test transactions |
| 2. Core screening endpoint | 25 min | POST /screening with all 5 checks |
| 3. Historical storage + query | 15 min | In-memory store, history endpoint, wire into screening |
| 4. Test data generation | 10 min | 100-150 transactions covering all scenarios |
| 5. Stretch goals (pick 1-2) | 15 min | Batch screening + configurable rules |
| 6. Documentation + demo | 10 min | README, demo script showing all 3 decision types |
| 7. Buffer | 5 min | Fix bugs, polish |

---

## Key Risks & Mitigations

1. **Fuzzy matching complexity** — Keep it simple. Normalize strings + Levenshtein distance. Don't over-engineer.
2. **Time pressure** — Core requirements first (65 points). Stretch goals only if time permits.
3. **Test data volume** — Script the generation of 100-150 transactions rather than hand-writing them.
4. **Structuring detection** — Need to think carefully about the algorithm: same sender, similar amounts (within 10-20% range?), within a time window (30 min).

---

## Summary

This is a well-scoped backend challenge. The core is a REST API with one main endpoint (transaction screening) that runs 5 compliance checks against reference data and historical transactions. The heaviest lift is getting the compliance logic right (50 points combined). Everything else — storage, code quality, docs, test data — is execution speed.

**Priority order**: Screening logic > Test data > Historical tracking > Documentation > Stretch goals.
