# Reproducibility checklist

1. Create the pinned environment.
2. Verify checksums with `MANIFEST.csv`.
3. Run `python verify_source_data.py` (39/39 checks expected).
4. Run `python verify_residual_identity.py` (all identities expected at numerical precision).
5. Use `docs/CODE_INDEX.md` to locate the script and derived table for each manuscript claim.
6. For a raw rerun, obtain the external inputs listed in `data/external/README.md`, then follow the Level 3 order in the repository README.
7. Confirm that regenerated headline numbers match `output/experiments/numerical_audit/numerical_audit.csv` and the Source Data workbook.
