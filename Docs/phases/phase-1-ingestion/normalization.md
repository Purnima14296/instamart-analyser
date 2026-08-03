## Phase 1 Normalization Rules

Applied after raw ingestion. Raw data is preserved in `raw_feedback`; cleaned data lives in `normalized_feedback`.

| Rule | Description |
|---|---|
| **Min words** | Keep reviews with **more than 4 words** (5+ words) |
| **English only** | Remove non-English reviews (Hindi, Tamil, etc.) |
| **No emojis** | Strip emoji characters from title and body |

## Run normalization

```powershell
$env:PYTHONPATH="src"

# Normalize all raw reviews
py -m instamart_analyser.phases.phase_1.pipeline normalize

# Export cleaned dataset
py -m instamart_analyser.phases.phase_1.export_reviews
```

Normalization also runs automatically at the end of `pipeline run`.

## Storage

| Table | Contents |
|---|---|
| `raw_feedback` | All ingested Instamart reviews (unchanged) |
| `normalized_feedback` | English, 5+ words, emoji-free reviews |
| `normalization_rejects` | Rejected records with reason (`too_short`, `non_english`, `empty_after_cleaning`) |
