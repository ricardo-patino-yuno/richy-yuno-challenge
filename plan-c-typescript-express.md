# Plan C: TypeScript + Express

## Stack

- **Language**: TypeScript 5.x
- **Runtime**: Node.js 20 (or Bun for speed)
- **Framework**: Express.js
- **Fuzzy Matching**: `fastest-levenshtein` npm package (fast native implementation)
- **Storage**: In-memory (Maps + arrays)
- **Validation**: Zod schemas
- **Test Data**: JSON files imported directly

---

## Project Structure

```
yuno-challenge/
├── src/
│   ├── index.ts              # Express app setup, route mounting, startup
│   ├── types.ts              # TypeScript interfaces & Zod schemas
│   ├── screening/
│   │   ├── engine.ts         # Core screening orchestrator
│   │   ├── rules/
│   │   │   ├── sanctions.ts      # Sanctions matching
│   │   │   ├── countryRisk.ts    # High-risk country check
│   │   │   ├── velocity.ts       # Transaction velocity check
│   │   │   ├── amount.ts         # Large amount check
│   │   │   └── structuring.ts    # Structuring pattern detection
│   │   └── scorer.ts         # Score aggregation + decision
│   ├── store/
│   │   └── memoryStore.ts    # In-memory transaction store (singleton)
│   └── routes/
│       ├── screening.ts      # POST /screening, POST /screening/batch
│       ├── transactions.ts   # GET /transactions
│       ├── rules.ts          # GET/PUT /rules (stretch)
│       └── audit.ts          # GET /audit (stretch)
├── data/
│   ├── sanctions-list.json
│   ├── high-risk-countries.json
│   └── test-transactions.json
├── scripts/
│   └── generate-test-data.ts # Script to generate 120 test transactions
├── demo.sh
├── package.json
├── tsconfig.json
└── README.md
```

---

## Implementation Order

### Phase 1: Scaffold + Data (12 min)
1. `npm init -y && npm i express zod fastest-levenshtein && npm i -D typescript @types/express @types/node tsx`
2. Minimal `tsconfig.json` (strict mode, ES2022 target)
3. Create data JSON files (sanctions, countries)
4. Define TypeScript interfaces + Zod schemas for request/response
5. Basic Express app with health endpoint, run with `tsx`

### Phase 2: Screening Engine (25 min)
1. Each rule is a function: `(ctx: ScreeningContext) => RuleResult`
   - `RuleResult = { scoreDelta: number, reasons: string[], matchedRules: string[] }`
   - `ScreeningContext` holds the request + store reference + config
2. Implement rules:
   - `checkSanctions` — normalize strings, use `fastest-levenshtein` with distance threshold
   - `checkCountry` — `Set.has()` lookup
   - `checkVelocity` — filter store by sender + time window, count
   - `checkAmount` — simple threshold
   - `checkStructuring` — filter by sender + 30min window, check amount similarity (within 20%)
3. `engine.ts` runs all rules in sequence, accumulates results
4. Decision logic: sanctions → DENIED; total score >= 50 → REVIEW; else APPROVED
5. Wire to POST `/api/screening`

### Phase 3: Historical Storage (12 min)
1. `MemoryStore` class (singleton):
   - `Map<string, Transaction[]>` keyed by normalized sender name
   - `add(tx)`, `getBySender(name, sinceMs)`, `getAll(since, until)`
2. Store each transaction after screening
3. GET `/api/transactions/:sender` with `?hours=24` query param
4. Velocity + structuring rules receive store instance

### Phase 4: Test Data (10 min)
1. `generate-test-data.ts` script to output 120 JSON transactions:
   - Same categories as other plans
   - Run once: `npx tsx scripts/generate-test-data.ts > data/test-transactions.json`

### Phase 5: Stretch Goals (15 min)
- **Batch screening**: `POST /api/screening/batch` — map over array, collect results, build summary
- **Configurable rules**: Rules config in `data/rules-config.json`, loaded at startup, PUT endpoint to update
- **Audit trail**: Array of `AuditEntry` objects, GET `/api/audit?from=&to=&transactionId=`

### Phase 6: Documentation + Demo (10 min)
1. README with `npm install && npx tsx src/index.ts`, endpoint table, architecture description
2. `demo.sh` with curl commands

---

## Fuzzy Matching Approach

```typescript
import { distance } from 'fastest-levenshtein';

function isSanctionsMatch(
  name: string,
  sanctionsList: string[],
  maxDistance: number = 3
): { match: boolean; matchedName?: string } {
  const normalized = name.toLowerCase().trim();
  for (const sanctioned of sanctionsList) {
    const d = distance(normalized, sanctioned.toLowerCase().trim());
    if (d <= maxDistance) {
      return { match: true, matchedName: sanctioned };
    }
  }
  return { match: false };
}
```

---

## Key Design Decisions

- **tsx for running** — no compilation step, TypeScript runs directly, faster dev loop
- **Zod for validation** — runtime validation with type inference, better error messages than manual checks
- **fastest-levenshtein** — fastest JS Levenshtein implementation, native-speed
- **Singleton store** — simple pattern, no dependency injection needed for this scope
- **Rules as pure functions** — each takes context, returns result, composable and testable
- **Express over Fastify** — more boilerplate but universally known, no surprises

---

## Dependencies

```json
{
  "dependencies": {
    "express": "^4.21.0",
    "fastest-levenshtein": "^1.0.16",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "@types/express": "^4.17.21",
    "@types/node": "^22.0.0",
    "tsx": "^4.19.0"
  }
}
```
