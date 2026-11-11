# Data Directory

- `generated/` — deterministic synthetic seed exports, manifests, and table
  checksums.
- `ground_truth/` — separate expected outcomes and isolated anomaly fixtures;
  never load these labels into application tables or decision inputs.
- `validation/` — generated-data validation and reproducibility reports.

Run the generator and validators from `backend/`. See
[`docs/database/seed-data-guide.md`](../docs/database/seed-data-guide.md) for
profiles, database safeguards, commands, synthetic-only provenance, and
reproducibility instructions.
