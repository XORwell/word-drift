# Human IAA round - instructions

Sample size: 50 hypotheses (stratified by language x evidence tier, seed 20260524).

1. Read `docs/annotation-guidelines.md` (the codebook) first.
2. Each rater independently fills `human-sheet.csv`: `q1_plausible_yes_no` (yes/no) and `q2_evidence_tier_1to5` (1-5). Add a one-line `notes` for any no.
3. Raters must NOT see each other's sheets or the curator's confidence (kept in `human-key.json`, not in the sheet).
4. Save each rater's file as `human-sheet-<rater>.csv`.
5. Score with `kappa.py` (extend it to read the human sheets the same way it reads the LLM annotations); report Cohen's kappa + Krippendorff's alpha and compare to the LLM pilot in `data/reports/iaa-pilot.md`.
