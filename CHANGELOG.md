# Changelog

## v1.1 (unreleased)

Two jobs: replace the unsourced SaaS retention benchmarks with sourced figures (decision D12), and make reruns of `python run_all.py` byte-for-byte identical.

### Benchmarks (D12, D28)

- Not replaced. This session's network policy blocked every benchmark publisher I tried (SaaS Capital, Benchmarkit, ChartMogul, High Alpha, Recurly and KeyBanc), so no primary source could be opened. The 4d ranges keep their "indicative, not sourced" label, and no figures were taken from search summaries or from memory. D12 lists each URL tried, and D28 records the fallback.
- Added `tests/test_benchmarks.py`. It checks that the databook's benchmark rows match the table they are read from, and that the memo, key findings, README and interview prep say nothing about benchmarks while none are sourced. Two further checks, on `outputs/tables/benchmarks.csv` and on the removal of the indicative label, skip with a reason until sourced figures exist.

### Byte-stable reruns (D29 to D34)

- A second run of `python run_all.py` now leaves every tracked file byte-for-byte unchanged. Before this, the ten notebooks, the databook, the memo docx and the memo PDF changed on every run.
- New `tools/`: `normalise_ooxml.py` (xlsx and docx), `normalise_pdf.py` and `normalise_notebook.py` fix the save-time stamps, LibreOffice's random chart axis ids, the zip layout, the PDF `/ID` and `/DocChecksum`, and the notebook timing metadata. `check_reproducible.py` runs the pipeline twice and explains any file that differs.
- `report_config.json` has a `document_date` (the v1.0 release date), which is the only date written into file metadata.
- `run_all.py` gives child processes `PYTHONHASHSEED=0`, runs notebooks without timing metadata, and has a `--check-determinism` flag.
- Explicit ordering: `ORDER BY` on the analysis queries and CSV exports, ordinals on multi-row `UNION ALL` tables, and `sorted()` where a set fed a floating-point sum. This fixed one printed value in the 04e notebook that flipped between `0.0` and `-0.0`.
- The step 2 and step 3 tables are now exported through the same six-decimal rounding as the others.
- Tests: `tests/test_reproducible.py` (marked slow, run with `python -m pytest tests -m slow`) checks that a rerun leaves `git status` unchanged. `pytest.ini` registers the marker.
- `requirements.txt` adds `lxml` and `pikepdf`.
- Every file in `outputs/tables/` and `outputs/charts/` is byte-identical to v1.0, so no figure, finding or rating changed.

## v1.0 (26 September 2026)

A self-directed simulation of buy-side financial due diligence on Northbridge Software Ltd, a fictional UK B2B SaaS company with about £40m of revenue, built on synthetic data. The release contains the data preparation pipeline in DuckDB SQL (load, profile, clean and a revenue cube, with the same steps written up for Alteryx), a month-by-month reconciliation of invoices to the management accounts, and the core commercial analyses as executed notebooks: revenue quality, customer concentration, cohorts, NRR and GRR, the ARR bridge, margins and segments. It also contains an Excel databook built from those outputs and recalculated in LibreOffice with its own checks tab, a Power BI build plan with DAX measures and expected values, a two-page findings memo in Word and PDF, and a README, CV bullets and interview prep generated from the same figures. Every number in the deliverables comes from the pipeline, and 106 pytest tie-outs check them. `python run_all.py` rebuilds everything from the raw data in about a minute.
