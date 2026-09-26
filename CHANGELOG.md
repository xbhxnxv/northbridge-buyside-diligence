# Changelog

## v1.1 (unreleased)

Two jobs: replace the unsourced SaaS retention benchmarks with sourced figures (decision D12), and make reruns of `python run_all.py` byte-for-byte identical.

### Benchmarks (D12, D28, D35 to D39)

- First attempt: not replaced. That session's network policy blocked every benchmark publisher tried, so the 4d ranges kept their indicative, unsourced label and nothing quoted a benchmark (D28).
- Retry, with the publishers' domains allowed: the ranges are replaced by figures read from SaaS Capital (2025 retention benchmarks, with the 2023 edition as context), High Alpha (2025 SaaS Benchmarks Report), Benchmarkit (2025 B2B SaaS Performance Metrics Benchmarks) and ChartMogul (SaaS Retention Report, 2023, context only). KeyBanc/Sapphire and Recurly were still unreachable (D35).
- New checked-in input `data/reference/benchmarks_source.csv` (151 rows: source, segment, metric, statistic, with URL, year and accessed date). The 04d notebook validates it and writes `outputs/tables/benchmarks.csv`, `4d_benchmark_comparison.csv`, `4d_northbridge_acv.csv`, the chart `outputs/charts/4d_benchmarks.png` and `docs/benchmarks.md`. `4d_benchmarks_indicative.csv` is removed. No network calls during a run (D39).
- SMB comparison adopted: medians for ACV bands under $50k in the 2025 editions, with SaaS Capital shown on its own because its definitions match ours (D36, D37). Northbridge's 2025 NRR and GRR are below SaaS Capital's SMB medians, and NRR before the price increase is below every SMB median.
- Databook 4d tab: the benchmark block reads `benchmarks.csv`, recomputes the SMB range with formulas, checks it against the notebook (three new TRUE checks) and carries a source note. The Summary tab's limitation line is updated. Still marked DRAFT.
- Key finding F03, the memo's NRR finding (with a source footnote) and the interview prep (a new follow-up on how Northbridge compares with the market) quote the sourced figures. No materiality rating, red-flag rating or recommendation changed (D38). The memo is still two pages.
- `docs/metric_definitions.md` has a Benchmarks section pointing to `docs/benchmarks.md`.
- Tests: the two benchmark checks that skipped now run and pass; new checks tie `benchmarks.csv` to the checked-in source, recompute the comparison, and tie every benchmark figure in the memo, key findings, interview prep, `docs/benchmarks.md` and the databook to `benchmarks.csv`. The checks for the unsourced state now skip.

### Byte-stable reruns (D29 to D34)

- A second run of `python run_all.py` now leaves every tracked file byte-for-byte unchanged. Before this, the ten notebooks, the databook, the memo docx and the memo PDF changed on every run.
- New `tools/`: `normalise_ooxml.py` (xlsx and docx), `normalise_pdf.py` and `normalise_notebook.py` fix the save-time stamps, LibreOffice's random chart axis ids, the zip layout, the PDF `/ID` and `/DocChecksum`, and the notebook timing metadata. `check_reproducible.py` runs the pipeline twice and explains any file that differs.
- `report_config.json` has a `document_date` (the v1.0 release date), which is the only date written into file metadata.
- `run_all.py` gives child processes `PYTHONHASHSEED=0`, runs notebooks without timing metadata, and has a `--check-determinism` flag.
- Explicit ordering: `ORDER BY` on the analysis queries and CSV exports, ordinals on multi-row `UNION ALL` tables, and `sorted()` where a set fed a floating-point sum. This fixed one printed value in the 04e notebook that flipped between `0.0` and `-0.0`.
- The step 2 and step 3 tables are now exported through the same six-decimal rounding as the others.
- Tests: `tests/test_reproducible.py` (marked slow, run with `python -m pytest tests -m slow`) checks that a rerun leaves `git status` unchanged. `pytest.ini` registers the marker.
- `requirements.txt` adds `lxml` and `pikepdf`.
- The rerun work changed no table or chart: after it, every file in `outputs/tables/` and `outputs/charts/` was byte-identical to v1.0. The benchmark work above then added the benchmark tables and chart and changed F03's text and `key_figures.csv`.

## v1.0 (26 September 2026)

A self-directed simulation of buy-side financial due diligence on Northbridge Software Ltd, a fictional UK B2B SaaS company with about £40m of revenue, built on synthetic data. The release contains the data preparation pipeline in DuckDB SQL (load, profile, clean and a revenue cube, with the same steps written up for Alteryx), a month-by-month reconciliation of invoices to the management accounts, and the core commercial analyses as executed notebooks: revenue quality, customer concentration, cohorts, NRR and GRR, the ARR bridge, margins and segments. It also contains an Excel databook built from those outputs and recalculated in LibreOffice with its own checks tab, a Power BI build plan with DAX measures and expected values, a two-page findings memo in Word and PDF, and a README, CV bullets and interview prep generated from the same figures. Every number in the deliverables comes from the pipeline, and 106 pytest tie-outs check them. `python run_all.py` rebuilds everything from the raw data in about a minute.
