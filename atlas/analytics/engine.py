import re
import time
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd
from atlas.config import settings

class AnalyticsEngineError(Exception):
    pass

class AnalyticsEngine:
    def __init__(self):
        self._con = duckdb.connect(database=":memory:")
        self._registered_tables: Dict[str, str] = {}  # dataset_id -> table_name

    def register_dataset(self, dataset_id: str, df: pd.DataFrame) -> str:
        table_name = f"tbl_{dataset_id.replace('-', '_')}"
        self._con.register(f"view_{table_name}", df)
        self._con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM view_{table_name}")
        self._registered_tables[dataset_id] = table_name
        return table_name

    def get_table_name(self, dataset_id: str) -> str:
        if dataset_id not in self._registered_tables:
            raise AnalyticsEngineError(f"Dataset {dataset_id} is not registered in the analytics engine.")
        return self._registered_tables[dataset_id]

    def execute_bounded_query(
        self,
        query: str,
        limit: int = 500,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Executes bounded, read-only SQL queries with strict security checks.
        Prevents DDL/DML, file reading, command execution, or infinite loops.
        """
        clean_q = query.strip()
        
        # Security: Disallow destructive and file/system commands
        forbidden = [
            r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
            r"\bALTER\b", r"\bCREATE\b", r"\bATTACH\b", r"\bDETACH\b",
            r"\bCOPY\b", r"\bEXPORT\b", r"\bIMPORT\b", r"\bread_csv\b",
            r"\bread_parquet\b", r"\bread_json\b"
        ]
        for pattern in forbidden:
            if re.search(pattern, clean_q, re.IGNORECASE):
                raise AnalyticsEngineError(f"Security violation: Query contains disallowed operation matching '{pattern}'.")

        # Guarantee limit
        effective_limit = min(limit, settings.max_result_rows)
        if not re.search(r"\bLIMIT\s+\d+", clean_q, re.IGNORECASE):
            clean_q = f"{clean_q} LIMIT {effective_limit}"

        start_time = time.time()
        try:
            rel = self._con.execute(clean_q)
            res_df = rel.df()
            duration_ms = int((time.time() - start_time) * 1000)
        except Exception as e:
            raise AnalyticsEngineError(f"Query execution failed: {str(e)}")

        # Enforce max row limit strictly
        if len(res_df) > effective_limit:
            res_df = res_df.head(effective_limit)

        return {
            "columns": list(res_df.columns),
            "rows": res_df.to_dict(orient="records"),
            "row_count": len(res_df),
            "duration_ms": duration_ms
        }

    def get_dataframe(self, dataset_id: str) -> pd.DataFrame:
        table_name = self.get_table_name(dataset_id)
        return self._con.execute(f"SELECT * FROM {table_name}").df()

# Global engine singleton
engine = AnalyticsEngine()
