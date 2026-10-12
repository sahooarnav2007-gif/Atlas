# Evaluation & Generalization Framework

ATLAS is evaluated across multiple criteria:

1. **Tool Correctness:**
   - Calculations match deterministic reference implementations (DuckDB, SciPy, scikit-learn).
   - Zero hallucinated numerical outputs.
2. **Schema Agnosticism:**
   - Evaluated on completely unseen schemas (e.g. IoT telemetry, finance, retail).
   - Dynamically discovers column roles rather than expecting predefined names.
3. **Cross-Session Memory Impact:**
   - Evaluated by asserting that a memory rule defined in Session A strictly alters numerical computation results in Session B.
4. **Security & Boundary Integrity:**
   - Prevents arbitrary SQL execution and system command injection.
   - Restricts oversized uploads and invalid parameters.
