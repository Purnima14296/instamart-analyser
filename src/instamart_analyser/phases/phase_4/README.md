# Phase 4: Recommendation Framing

Status: **implemented**

Implementation lives in `src/instamart_analyser/phases/phase_4/`.  
Data output is stored in `data/phase-4/`.

Key outputs:

- `opportunity-map.json`
- `hypothesis-backlog.json`
- `phase-4-summary.json`
- `experiment-framing-memo.md`

Run:

```powershell
$env:PYTHONPATH="src"
py -m instamart_analyser.phases.phase_4.pipeline run
py -m instamart_analyser.phases.phase_4.validate_phase4
```

See `Docs/implementationplan.md` and `Docs/phases/phase-4-recommendation-framing/eval.md`.
