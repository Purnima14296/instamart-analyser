# Optional daily enrichment resume helper (Phase 6C)

When Groq quota resets, run:

```powershell
cd "c:\Users\purni\Instamart Analyser"
$env:PYTHONPATH="src"
py -m instamart_analyser.phases.phase_2.pipeline enrich
py -m instamart_analyser.phases.phase_3.pipeline run --dry-run --limit 8
py -m instamart_analyser.phases.phase_4.pipeline run
py -m instamart_analyser.phases.phase_5.pipeline run
```

Or use Admin → Jobs in the dashboard.
