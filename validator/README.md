# ER Diagram Validator (v1)

Validates a **student's** ER diagram against a **teacher's** reference model by
**colored-graph isomorphism**, using the real native engines:

- **Bliss** — vendored from [digraphs/bliss](https://github.com/digraphs/bliss) (strong on graphs with deep symmetry)
- **Saucy** — vendored from [hrbrmstr/saucy](https://github.com/hrbrmstr/saucy) (strong on sparse graphs)

No algorithm code was rewritten. Both diagrams come straight from the
drawdb-clone editor's **Save (JSON export)** button.

## Setup (one time)

```bash
cd validator
bash setup.sh                      # clones + compiles bliss and saucy (needs cc, make, git)
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Run

```bash
# HTTP API (what the frontend calls)
./.venv/bin/uvicorn er_validator.api:app --port 8000

# CLI
./.venv/bin/python -m er_validator.cli teacher.json student.json --algorithm saucy
# exit codes: 0 valid, 1 not valid, 2 error

# tests (both engines)
./.venv/bin/python -m pytest tests/
```

### API

`POST /validate`
```json
{ "teacher": <editor export>, "student": <editor export>, "algorithm": "bliss" }
```
`algorithm` is optional — falls back to the `VALIDATOR_ALGORITHM` env var, then `"bliss"`.

Response:
```json
{
  "is_valid": false,
  "algorithm_used": "Bliss",
  "mismatches": [
    { "code": "field_types",
      "message": "teacher has 1 field(s) of INT [NOT NULL]; student has 0",
      "teacher": 1, "student": 0 }
  ],
  "names": { "score": 100, "matched": [...], "missing": [], "extra": [],
             "scoring_breakdown": { ... } },
  "stats": { "teacher_nodes": 13, "student_nodes": 13,
             "teacher_edges": 15, "student_edges": 15,
             "engine_ran": false, "engine_ms": null }
}
```

`GET /health` reports whether both native binaries are ready.

## Entity name comparison (`er_validator/name_matcher.py`)

Structural validation ignores names entirely, so every `/validate` response also
carries a `names` report comparing table names (approach adapted from
[Entity_engine](https://github.com/Divyapahuja31/Entity_engine)). Each name is
normalized — camelCase split, lowercased, punctuation stripped, last word
singularized (`OrderDetails` → `order detail`) — then matched in three stages:

1. **exact** — identical normalized forms (`Orders` ↔ `order`);
2. **semantic** — both names in the same synonym group of
   `er_validator/ontology.json` (`Customer` ↔ `Client`);
3. **fuzzy** — `max(Jaro-Winkler, Levenshtein)` similarity ≥ 0.8, closest
   pairs matched first (`Custommer` ↔ `Customer`).

Unmatched teacher names are `missing`, unmatched student names `extra`. The
0–100 `score` weights matches per stage (exact/semantic 100, fuzzy 80) over the
teacher's table count, minus penalties (extra 1.67 each, missing 0 by default).
The report is advisory: `is_valid` stays purely structural.

`POST /compare-names` exposes the matcher directly:
```json
{ "teacher": ["Customer", "Orders"], "student": ["client", "order"],
  "weights": {"fuzzy": 80}, "penalties": {"extra": 1.67}, 
  "similarity_threshold": 0.8, "custom_ontology": [["gadget", "widget"]] }
```
(all fields but `teacher`/`student` optional) → `{"score", "matched", "missing",
"extra", "scoring_breakdown"}`.

## How diagrams become graphs (`er_validator/graph_builder.py`)

- **Node per field**, colored by `(data_type, PK, NOT NULL, UNIQUE, AUTO_INCREMENT)`.
  Names, positions and display colors are ignored — a correctly-structured diagram
  with different naming still passes (v1 decision; name matching is a v2 flag).
- **Same-table fields** are joined into a clique (entity membership).
- **Each relationship** becomes a chain `startField — FK_SRC — FK_DST — endField`;
  the two marker nodes carry direction + cardinality as colors, because Bliss and
  Saucy color vertices, not edges.

## How two automorphism tools answer an isomorphism question

Bliss and Saucy compute **automorphism groups** of one graph; neither compares two
graphs directly. `engines/native.py` uses the standard reduction: build
`H = G_teacher ⊎ G_student` plus two apex vertices of a unique shared color (apex1
joined to every teacher vertex, apex2 to every student vertex). Then

```
G_teacher ≅ G_student  ⇔  apex1 and apex2 lie in the same orbit of Aut(H)
```

and orbits are a union-find over the generator permutations the tools print.
The apexes keep this correct even for disconnected diagrams.

## Swapping algorithms (Strategy pattern)

`engines/base.py` defines the `IsomorphismEngine` interface and the registry
`ENGINES = {"bliss": BlissEngine, "saucy": SaucyEngine}`. The two engines share all
logic via `NativeGroupEngine` and differ only in:

| | input format | binary | cycle numbering |
|---|---|---|---|
| `BlissEngine` | DIMACS (`p edge`, `n v c`, `e u v`) | `vendor/bliss/bliss` | 1-based |
| `SaucyEngine` | saucy "amorph" (`n e p`, color blocks, edges) | `vendor/saucy_bin` | 0-based |

Adding another backend (e.g. nauty) = one small subclass + one registry line.
Binary paths resolve as: `BLISS_BIN`/`SAUCY_BIN` env var → `vendor/paths.json` → default.

## Pipeline

1. `schema.py` — parse/validate the export JSON (bad input → 422 with a reason).
2. `graph_builder.py` — build both colored graphs with a **shared** color table.
3. `diagnostics.py` — cheap invariants (counts, field-type multisets, table
   compositions, cardinalities, relationship endpoint signatures). Any difference
   short-circuits to `is_valid: false` **and** produces the human-readable
   `mismatches` — more useful to a student than a bare "no".
4. Only if all invariants agree does the chosen engine run; a failure there yields
   the single `structural` mismatch (right pieces, wrong wiring).

## Notes & licenses

- `vendor/saucy_cli.c` is ours: the upstream saucy repo wraps the engine for R, so
  we drive the untouched engine (`vendor/saucy/src/ssaucy.c`) with a ~100-line
  stdio front end instead.
- Saucy's license (see `vendor/saucy/LICENSE`) permits research/education use —
  fine here, review before any commercial deployment. Bliss is LGPL-3.0.
- v2 ideas: name normalization/fuzzy matching, witness mapping (which student field
  ↔ which teacher field), partial-credit scoring, a Validate button in the editor.

## Question portal (prototype)

The API also stores teacher-authored questions in `validator/portal.db` (SQLite,
created automatically). The React editor front-ends this as a portal: pick
**Teacher** (write a problem statement, draw the reference diagram on the canvas,
publish) or **Student** (pick a question, draw, submit — the validator grades it).

| endpoint | who | what |
|---|---|---|
| `GET /questions` | both | list questions (id, title, created_at) |
| `POST /questions` | teacher | `{title, prompt, reference}` — reference is the editor export |
| `GET /questions/{id}` | student | prompt only; `?include_reference=true` for teachers |
| `DELETE /questions/{id}` | teacher | remove a question |
| `POST /questions/{id}/submit` | student | `{student, algorithm?}` → validation verdict |

No auth in v1 — the frontend role picker only gates the UI. Add real accounts
before using this with a live class.
