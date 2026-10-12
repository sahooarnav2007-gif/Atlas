# Persistent Domain Memory Design

ATLAS implements domain memory rather than conversational chat history.

## What is Stored
1. **Metric Definitions:** E.g., `active_customer = (customer_status != 'cancelled')`
2. **Column Semantics:** Mapping cryptic column names and units.
3. **Reusable Filters:** Named business cohorts (e.g. `enterprise_active`).
4. **Analysis Preferences:** Aggregation granularities and formatting preferences.

## Lifecycle & Versioning
- **Scoped:** Tied to a `dataset_family` or specific column names.
- **Versioned:** When a definition is updated, previous versions are marked `status = 'superseded'` and link to `superseded_by`.
- **Active State:** Only `status = 'active'` records are injected into the agent orchestrator.
- **Cross-Session Verification:** Changes stored in Session A persist in the database and directly alter SQL WHERE clauses and calculation results in Session B.
