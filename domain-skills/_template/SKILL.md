# _template — domain skill scaffold

Copy this folder to start a new domain skill. The canonical shape is:

```
<domain-name>/
├── SKILL.md            # what the skill does, what it consumes/produces
├── skill.py            # optional: per-domain extraction code
└── fixtures/
    └── case_<NNN>/
        ├── inputs/             # raw artifacts the skill consumes (HTML, JSON, parquet, FITS, ...)
        ├── expected.json       # MANDATORY: predicates (predicate-first, not byte-exact)
        ├── floor.json          # OPTIONAL: hardware minimum
        ├── tolerances.json     # OPTIONAL: per-profile rtol/atol/cosine_min
        ├── cache.json          # OPTIONAL: VCR cassette for LLM/VLM/network calls
        └── README.md           # what this case exercises
```

`dh check-skill <skill-path>` is the hard gate. Predicate-first; replay-only on cassettes.
