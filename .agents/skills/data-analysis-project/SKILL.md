---
name: data-analysis-project
description: Use for datasets, logs, spreadsheets, or metrics work that should stay reproducible, quality-checked, and explicit about interpretation limits.
---

# Data analysis project

## Trigger

- Use for CSV, JSON, logs, spreadsheets, KPI extracts, or other structured data work.
- Use when conclusions should come from repeatable analysis rather than ad hoc inspection.

## Inputs

- Raw datasets and file formats.
- Business or technical question.
- Units, date ranges, and known caveats.

## Workflow

1. Inventory sources and formats.
2. Check schema, missingness, duplicates, units, and obvious anomalies before interpreting results.
3. Keep raw inputs immutable.
4. Use reproducible scripts, notebooks, or documented transformations.
5. Label filters, assumptions, and derived fields.
6. Separate observed results from interpretation and recommendation.

## Stop / Approval Rules

- Stop before overwriting raw data.
- Stop if data quality is too weak for the claimed conclusion.
- Stop before exporting sensitive data outside the approved environment.

## Checks

- Raw data remains untouched.
- Analysis path is reproducible.
- Data quality caveats are attached to the result.
- Units and filters are explicit.

## Output

```text
## Question
...

## Inputs
- ...

## Method
- ...

## Results
- ...

## Data quality risks
- ...

## Reproduction
- ...
```
