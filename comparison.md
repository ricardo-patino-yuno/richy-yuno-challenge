# Plan Comparison: A vs B vs C

## Quick Reference

| Aspect | Plan A: Python + FastAPI | Plan B: Go + Gin | Plan C: TypeScript + Express |
|--------|--------------------------|-------------------|-------------------------------|
| Language | Python 3.12 | Go 1.22 | TypeScript 5.x |
| Framework | FastAPI | Gin | Express |
| Dependencies | 5 packages | 1 package | 4 prod + 3 dev |
| Fuzzy matching | `thefuzz` library | Custom (20 lines) | `fastest-levenshtein` |
| Validation | Pydantic v2 | Gin binding tags | Zod |
| Lines of code (est.) | ~400-500 | ~600-750 | ~500-600 |
| Setup time (est.) | ~3 min | ~5 min | ~5 min |

---

## Plan A: Python + FastAPI

### Advantages

1. **Fastest development speed** — Python is the most concise language of the three. Less boilerplate means more time for logic. Critical when you have 90 minutes.
2. **FastAPI auto-generates OpenAPI docs** — Free Swagger UI at `/docs`. This counts toward the documentation rubric (10 points) with zero extra effort.
3. **Pydantic validation is effortless** — Define a model, get automatic request validation, error messages, and type coercion. No manual parsing code.
4. **`thefuzz` is battle-tested** — Levenshtein + partial matching + token sorting built in. `fuzz.ratio()`, `fuzz.partial_ratio()`, `fuzz.token_sort_ratio()` cover edge cases you won't think of.
5. **Lowest risk of bugs** — Python's dynamic typing and conciseness means fewer lines = fewer places for bugs. With Pydantic, even the validation layer is nearly foolproof.
6. **Dict-based storage is trivial** — `defaultdict(list)` and you have a working store in 2 lines.

### Disadvantages

1. **Performance at scale is weakest** — Single-threaded by default. But irrelevant for this challenge (in-memory, no real load).
2. **Type safety is opt-in** — Despite type hints, Python won't catch type errors at compile time. Bugs surface at runtime.
3. **Dependency on `thefuzz`** — Requires `python-Levenshtein` C extension for speed. If the evaluator's system has compilation issues, it could fail to install.
4. **Less impressive from an engineering perspective** — Python is the "easy" choice. An evaluator at a company that values Go/Java might see it as taking the path of least resistance.

---

## Plan B: Go + Gin

### Advantages

1. **Signals engineering rigor** — Go is a systems language. Choosing it shows you can handle a statically-typed, compiled language under time pressure. This can favorably impress evaluators.
2. **Single binary deployment** — `go build` produces one binary with embedded data files. Zero runtime dependencies. The evaluator runs `./server` and it works. Simplest possible demo experience.
3. **Thread safety is explicit** — `sync.RWMutex` on the store shows you think about concurrency, even if it's not strictly needed. Demonstrates production mindset.
4. **Only 1 external dependency** (Gin) — Minimal supply chain, everything else is stdlib. Shows you don't reach for libraries for trivial problems.
5. **Compile-time type safety** — Struct types catch errors before runtime. No surprises during demo.
6. **`//go:embed` for data** — Data files compiled into the binary. No file path issues, no "where's the config?" problems.

### Disadvantages

1. **Slowest development speed** — Go is verbose. Error handling alone (`if err != nil { return }`) adds significant line count. Struct definitions, JSON tags, manual response building — it all adds up.
2. **Custom Levenshtein is a risk** — Writing your own fuzzy matching under time pressure introduces bug risk. Off-by-one errors in the DP matrix, unicode handling, edge cases.
3. **No auto-generated API docs** — You'd need to manually document endpoints in the README. No free Swagger UI.
4. **Boilerplate-heavy** — Gin handlers require manual JSON binding, error checking, response formatting. What's 3 lines in FastAPI is 15 in Go.
5. **Estimated 150-250 more lines of code** — More code = more time writing = less time for stretch goals and polish.
6. **Test data generation is clunkier** — No quick scripting; you'd either write a Go program or hand-craft JSON.

---

## Plan C: TypeScript + Express

### Advantages

1. **Strong typing + fast development** — TypeScript gives compile-time safety like Go but with JavaScript's development speed. Good middle ground.
2. **Zod gives runtime + compile-time validation** — Schema inference means you define once and get both runtime checks and TypeScript types. Very clean.
3. **npm ecosystem is vast** — `fastest-levenshtein` is fast and well-maintained. No need to write your own.
4. **`tsx` eliminates build step** — Run TypeScript directly. No `tsc && node dist/` dance. As fast to iterate as Python.
5. **JSON is native** — Loading JSON config files is a one-liner (`import data from './file.json'`). No marshaling, no struct tags.
6. **Familiar to most evaluators** — TypeScript/Node is widely used. Anyone can read and evaluate the code.

### Disadvantages

1. **Express is verbose for validation** — Unlike FastAPI, Express doesn't validate requests automatically. Zod helps but you still wire it manually.
2. **More dependencies than Go** — 7 packages total (prod + dev). Not a real problem, but more moving parts.
3. **No auto API docs** — Like Go, you'd write documentation manually. Could add `swagger-jsdoc` but that's more setup time.
4. **`node_modules` is messy** — The evaluator needs to `npm install` first. Not as clean as Go's single binary or Python's `pip install -r`.
5. **Express is dated** — Express 4.x is maintenance mode. Some evaluators might question why not Fastify, Hono, or Elysia. But Express is universally known and stable.
6. **Middle-of-the-road impression** — Doesn't signal the conciseness of Python or the rigor of Go. It's the "safe" choice.

---

## Head-to-Head Comparisons

### Development Speed (most important given time constraint)

```
Python + FastAPI  ████████████████████  (fastest)
TypeScript + Express  ██████████████████  (fast)
Go + Gin  ████████████████  (slower)
```

**Winner**: Python. Pydantic models + FastAPI decorators + `thefuzz` = least code for the same functionality. You'll finish 10-15 minutes faster than Go.

### Code Quality Impression

```
Go + Gin  ████████████████████  (strongest signal)
TypeScript + Express  ██████████████████  (solid)
Python + FastAPI  ████████████████  (fine, but "easy mode")
```

**Winner**: Go. Statically typed, compiled, explicit error handling — it reads like production code.

### Stretch Goal Feasibility

```
Python + FastAPI  ████████████████████  (most time left over)
TypeScript + Express  ██████████████████  (decent time left)
Go + Gin  ██████████████  (tight)
```

**Winner**: Python. Faster core implementation = more time for batch screening, configurable rules, and audit trail.

### Evaluator Demo Experience

```
Go + Gin  ████████████████████  (run one binary)
Python + FastAPI  ██████████████████  (pip install + run, but Swagger UI is free)
TypeScript + Express  ████████████████  (npm install + run)
```

**Winner**: Tie between Go (simplest run) and Python (auto Swagger docs).

### Risk of Time Overrun

```
Go + Gin  ████████████████████  (highest risk)
TypeScript + Express  ████████████████  (moderate)
Python + FastAPI  ██████████████  (lowest risk)
```

**Winner**: Python has the lowest risk of not finishing on time.

### Fuzzy Matching Quality

```
Python (thefuzz)  ████████████████████  (best: ratio + partial_ratio + token_sort)
TypeScript (fastest-levenshtein)  ████████████████  (good: raw distance)
Go (custom)  ██████████████  (acceptable but risky to implement)
```

**Winner**: Python. `thefuzz` provides multiple matching strategies out of the box.

---

## Scoring Projection (out of 100)

| Criterion (points) | Plan A: Python | Plan B: Go | Plan C: TypeScript |
|---------------------|---------------|------------|-------------------|
| Core functionality (25) | 25 | 23-25 | 24-25 |
| Compliance logic (25) | 24-25 | 22-24 | 23-25 |
| Historical tracking (15) | 15 | 14-15 | 14-15 |
| Code quality (10) | 8-9 | 9-10 | 8-9 |
| Test data (10) | 9-10 | 8-9 | 9-10 |
| Documentation (10) | 10 (Swagger free) | 8-9 | 8-9 |
| Stretch goals (5) | 4-5 | 2-3 | 3-4 |
| **Estimated Total** | **95-99** | **86-95** | **89-97** |

---

## Recommendation

**Plan A (Python + FastAPI) is the optimal choice** for this challenge. Here's why:

1. **Time is the biggest constraint.** You have 90 minutes for core + stretch. Python minimizes implementation time and maximizes time for polish, stretch goals, and documentation.
2. **Compliance logic is worth 50 points.** `thefuzz` gives you better fuzzy matching than a hand-rolled Levenshtein in Go, directly impacting the biggest scoring category.
3. **Free Swagger docs = free 10 points.** FastAPI's auto-generated OpenAPI documentation satisfies the documentation rubric with no extra work.
4. **Stretch goals become realistic.** With ~15 minutes saved vs Go, you can implement 2-3 stretch goals instead of maybe 1.
5. **Lowest risk.** Fewer lines of code, fewer bugs, fewer chances to get stuck on a syntax issue under pressure.

**Choose Go (Plan B) only if** you want to make a specific engineering impression and are confident you can absorb the extra 15 minutes of boilerplate.

**Choose TypeScript (Plan C) if** you're most comfortable with it and want type safety without Go's verbosity.

---

## Final Verdict

| Priority | Best Choice |
|----------|-------------|
| Maximize score | Plan A (Python) |
| Maximize engineering impression | Plan B (Go) |
| Balance speed + safety | Plan C (TypeScript) |
