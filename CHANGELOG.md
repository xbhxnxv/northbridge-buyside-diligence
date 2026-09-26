# Changelog

## v1.1 (unreleased)

Work in progress. Two jobs: replace the unsourced SaaS retention benchmarks with sourced figures (decision D12), and make reruns of `python run_all.py` byte-for-byte identical.

## v1.0 (26 September 2026)

A self-directed simulation of buy-side financial due diligence on Northbridge Software Ltd, a fictional UK B2B SaaS company with about £40m of revenue, built on synthetic data. The release contains the data preparation pipeline in DuckDB SQL (load, profile, clean and a revenue cube, with the same steps written up for Alteryx), a month-by-month reconciliation of invoices to the management accounts, and the core commercial analyses as executed notebooks: revenue quality, customer concentration, cohorts, NRR and GRR, the ARR bridge, margins and segments. It also contains an Excel databook built from those outputs and recalculated in LibreOffice with its own checks tab, a Power BI build plan with DAX measures and expected values, a two-page findings memo in Word and PDF, and a README, CV bullets and interview prep generated from the same figures. Every number in the deliverables comes from the pipeline, and 106 pytest tie-outs check them. `python run_all.py` rebuilds everything from the raw data in about a minute.
