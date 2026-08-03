## Source Category Mapping

Instamart-only ingestion: every record must explicitly mention **Instamart** or **Insta Mart**.

| Problem statement category | Phase 1 source | Notes |
|---|---|---|
| App Store / Play Store reviews | `play_store`, `app_store` | Swiggy app reviews filtered to Instamart mentions only |
| Product reviews | `mouthshut` | Instamart-specific MouthShut reviews |
| Community forums | `reddit`, `quora`, `facebook` | Instamart keyword filter applied |
| Social media | `youtube`, `twitter` | Seed data; Instamart mentions only |

**Excluded:** Blinkit, Zepto, and other competitor reviews. Generic Swiggy food-delivery reviews without an Instamart mention.

## Filter rule

```python
# Record is kept only if body or title contains:
"instamart" or "insta mart"
```

## Run

```powershell
$env:PYTHONPATH="src"
py -m instamart_analyser.phases.phase_1.pipeline run
```

Purge non-Instamart records from existing database:

```powershell
py -c "import sys; sys.path.insert(0,'src'); from instamart_analyser.phases.phase_1.storage import RawStore; s=RawStore(); print('Removed', s.purge_non_instamart())"
```
