# Plan B: Go + Gin

## Stack

- **Language**: Go 1.22
- **Framework**: Gin
- **Fuzzy Matching**: Custom Levenshtein implementation (no external dependency needed, ~20 lines)
- **Storage**: In-memory (`sync.RWMutex`-protected maps)
- **Validation**: Gin binding tags + custom validators
- **Test Data**: Embedded JSON files via `embed` package

---

## Project Structure

```
yuno-challenge/
├── cmd/
│   └── server/
│       └── main.go           # Entry point, server setup
├── internal/
│   ├── models/
│   │   └── models.go         # Request/response structs
│   ├── screening/
│   │   ├── engine.go         # Core screening orchestrator
│   │   ├── sanctions.go      # Sanctions matching
│   │   ├── country.go        # High-risk country check
│   │   ├── velocity.go       # Velocity check
│   │   ├── amount.go         # Amount threshold check
│   │   └── structuring.go    # Structuring detection
│   ├── store/
│   │   └── memory.go         # Thread-safe in-memory store
│   ├── config/
│   │   └── config.go         # Rules configuration loader
│   └── handlers/
│       ├── screening.go      # Screening HTTP handlers
│       ├── transactions.go   # Transaction history handlers
│       └── rules.go          # Rules CRUD handlers (stretch)
├── data/
│   ├── sanctions_list.json
│   ├── high_risk_countries.json
│   └── test_transactions.json
├── demo.sh
├── go.mod
├── go.sum
└── README.md
```

---

## Implementation Order

### Phase 1: Scaffold + Data (12 min)
1. `go mod init yuno-challenge` + `go get github.com/gin-gonic/gin`
2. Define structs: `TransactionRequest`, `ScreeningResponse`, `RuleResult`
3. Create JSON data files (sanctions, countries)
4. Basic Gin server with `/health` endpoint
5. Load reference data at startup via `//go:embed`

### Phase 2: Screening Engine (28 min)
1. Implement each rule as a method on a `ScreeningEngine` struct:
   - `CheckSanctions(name string) (int, []string, []string)` — custom Levenshtein + normalization
   - `CheckCountry(code string) (int, []string, []string)` — map lookup
   - `CheckVelocity(sender string, ts time.Time) (int, []string, []string)` — count from store
   - `CheckAmount(amount float64) (int, []string, []string)` — threshold comparison
   - `CheckStructuring(sender string, amount float64, ts time.Time) (int, []string, []string)` — window analysis
2. Orchestrator: `Screen(req TransactionRequest) ScreeningResponse`
   - Run all checks, aggregate scores
   - Determine decision: sanctions match → DENIED; score >= 50 → REVIEW; else APPROVED
3. POST `/api/screening` handler

### Phase 3: Historical Storage (15 min)
1. `MemoryStore` struct with `sync.RWMutex`:
   - `map[string][]StoredTransaction` keyed by normalized sender name
   - `Add(tx)`, `GetBySender(name, since time.Time)`, `GetAll(since, until)`
2. Store each transaction after screening
3. GET `/api/transactions/:sender` handler
4. Wire velocity + structuring to read from store

### Phase 4: Test Data (10 min)
1. Hand-craft a Go script or raw JSON with 120 transactions:
   - Same distribution as Plan A (clean, sanctions, velocity, structuring, country, amount)
   - Timestamp spread across 24+ hours

### Phase 5: Stretch Goals (12 min)
- **Batch screening**: Accept `[]TransactionRequest`, return `[]ScreeningResponse` + summary
- **Configurable rules**: `Config` struct loaded from JSON, exposed via GET/PUT `/api/rules`
- **Audit trail**: Every decision logged to in-memory slice, GET `/api/audit?from=&to=`

### Phase 6: Documentation + Demo (8 min)
1. README with `go run cmd/server/main.go` instructions, endpoint table, architecture
2. `demo.sh` with curl examples

---

## Fuzzy Matching Approach

```go
func levenshtein(a, b string) int {
    la, lb := len(a), len(b)
    d := make([][]int, la+1)
    for i := range d {
        d[i] = make([]int, lb+1)
        d[i][0] = i
    }
    for j := 1; j <= lb; j++ {
        d[0][j] = j
    }
    for i := 1; i <= la; i++ {
        for j := 1; j <= lb; j++ {
            cost := 0
            if a[i-1] != b[j-1] {
                cost = 1
            }
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
        }
    }
    return d[la][lb]
}

func isSanctionsMatch(name string, sanctionsList []string, maxDistance int) (bool, string) {
    normalized := strings.ToLower(strings.TrimSpace(name))
    for _, s := range sanctionsList {
        if levenshtein(normalized, strings.ToLower(s)) <= maxDistance {
            return true, s
        }
    }
    return false, ""
}
```

---

## Key Design Decisions

- **No ORM, no DB driver** — pure in-memory with mutex protection
- **`//go:embed` for data files** — single binary contains everything, zero config to run
- **Custom Levenshtein** — avoids external dependency for a 20-line function
- **Gin** — minimal framework, fast routing, built-in JSON binding/validation
- **Struct methods for rules** — engine holds config + store reference, rules are methods
- **Thread-safe store** — `sync.RWMutex` allows concurrent reads during screening

---

## Dependencies

```
github.com/gin-gonic/gin v1.10.0
```

Single dependency only.
