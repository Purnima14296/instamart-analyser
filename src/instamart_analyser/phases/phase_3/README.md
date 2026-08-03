# Phase 3: Theme Detection And Insight Generation

Status: **implemented**

Implementation lives in `src/instamart_analyser/phases/phase_3/`.  
Data output is stored in `data/phase-3/`.

## Commands

```powershell
$env:PYTHONPATH="src"

# Build deterministic clusters from Phase 2 enriched data
py -m instamart_analyser.phases.phase_3.pipeline aggregate

# Draft insights without Groq
py -m instamart_analyser.phases.phase_3.pipeline draft-insights --dry-run

# Full Phase 3 run
py -m instamart_analyser.phases.phase_3.pipeline run --dry-run

# Validate outputs
py -m instamart_analyser.phases.phase_3.validate_phase3
```

See `Docs/implementationplan.md` and `Docs/phases/phase-3-insight-generation/eval.md`.
