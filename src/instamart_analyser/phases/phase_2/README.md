# Phase 2: Cleaning, Normalization, And Enrichment

Status: **implemented**

Implementation: `src/instamart_analyser/phases/phase_2/`  
Data output: `data/phase-2/`

## Commands

```powershell
$env:PYTHONPATH="src"

# Build cohort (≤1000 reviews)
py -m instamart_analyser.phases.phase_2.pipeline build-cohort

# Export gold-set candidates for manual labeling
py -m instamart_analyser.phases.phase_2.pipeline gold-export

# Enrich (dry-run without API key)
py -m instamart_analyser.phases.phase_2.pipeline enrich --dry-run --limit 10

# Enrich with Groq micro-batches (default batch size 8; set GROQ_API_KEY first)
py -m instamart_analyser.phases.phase_2.pipeline enrich

# Check daily usage and progress
py -m instamart_analyser.phases.phase_2.pipeline status

# Export enriched JSONL
py -m instamart_analyser.phases.phase_2.pipeline export

# Validate Phase 2 exit criteria
py -m instamart_analyser.phases.phase_2.validate_phase2
```

See `Docs/implementationplan.md` and `Docs/phases/phase-2-enrichment/eval.md`.
