import re
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class MetricSpec(BaseModel):
    column: str
    aggregation: str = "sum"  # sum, avg, count, min, max, count_distinct
    alias: Optional[str] = None

class FilterSpec(BaseModel):
    column: str
    operator: str = "="  # =, !=, >, >=, <, <=, in, not in, like, is null, is not null
    value: Any = None

class SortSpec(BaseModel):
    column: str
    direction: str = "desc"  # asc or desc

class QueryDataInput(BaseModel):
    group_by: Optional[List[str]] = Field(default=None, description="Columns to group by")
    metrics: Optional[List[MetricSpec]] = Field(default=None, description="Metric aggregations")
    filters: Optional[List[FilterSpec]] = Field(default=None, description="Structured filters to apply")
    sort_by: Optional[List[SortSpec]] = Field(default=None, description="Sorting criteria")
    limit: int = Field(default=100, description="Max rows to return")
    sql_filter: Optional[str] = Field(default=None, description="Optional raw SQL WHERE clause filter expression")

def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

@registry.register("query_data", QueryDataInput)
def query_data(
    dataset_id: str,
    group_by: Optional[List[str]] = None,
    metrics: Optional[List[Any]] = None,
    filters: Optional[List[Any]] = None,
    sort_by: Optional[List[Any]] = None,
    limit: int = 100,
    sql_filter: Optional[str] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validated filtering, grouping, aggregation, sorting, top-N, and distinct counts.
    """
    tbl = engine.get_table_name(dataset_id)
    warnings: List[str] = []

    where_clauses: List[str] = []
    
    # Process structured filters
    if filters:
        for f in filters:
            f_col = _get_val(f, "column")
            f_op = str(_get_val(f, "operator", "=")).upper().strip()
            f_val = _get_val(f, "value")
            col_safe = f'"{f_col}"'

            if f_op == "IS NULL":
                where_clauses.append(f"{col_safe} IS NULL")
            elif f_op == "IS NOT NULL":
                where_clauses.append(f"{col_safe} IS NOT NULL")
            elif f_op in {"=", "!=", ">", ">=", "<", "<="}:
                if isinstance(f_val, str):
                    val_clean = f_val.replace("'", "''")
                    where_clauses.append(f"{col_safe} {f_op} '{val_clean}'")
                elif f_val is None:
                    where_clauses.append(f"{col_safe} IS NULL" if f_op == "=" else f"{col_safe} IS NOT NULL")
                else:
                    where_clauses.append(f"{col_safe} {f_op} {f_val}")
            elif f_op == "IN" and isinstance(f_val, list):
                vals_str = ", ".join(f"'{str(v).replace('\'', '\'\'')}'" if isinstance(v, str) else str(v) for v in f_val)
                where_clauses.append(f"{col_safe} IN ({vals_str})")
            elif f_op == "LIKE":
                val_clean = str(f_val).replace("'", "''")
                where_clauses.append(f"{col_safe} LIKE '{val_clean}'")
            else:
                warnings.append(f"Ignored unsupported filter operator '{f_op}' for column {f_col}")

    # Process additional SQL filter (e.g. from memory rules)
    if sql_filter:
        clean_sf = sql_filter.strip()
        # Security sanitization on custom filter
        if any(w in clean_sf.upper() for w in ["DROP", "DELETE", "UPDATE", "INSERT", ";"]):
            warnings.append("Security warning: Disallowed tokens in sql_filter; ignored.")
        else:
            where_clauses.append(f"({clean_sf})")

    # Build SELECT clause
    select_items = []
    if group_by:
        for gb in group_by:
            select_items.append(f'"{gb}"')

    if metrics:
        agg_map = {
            "sum": "SUM", "avg": "AVG", "mean": "AVG",
            "count": "COUNT", "min": "MIN", "max": "MAX",
            "count_distinct": "COUNT(DISTINCT",
            "distinct_count": "COUNT(DISTINCT"
        }
        for m in metrics:
            m_agg = str(_get_val(m, "aggregation", "sum")).lower()
            m_col = _get_val(m, "column")
            m_alias = _get_val(m, "alias")
            agg_fn = agg_map.get(m_agg, "SUM")
            col_target = f'"{m_col}"' if m_col != "*" else "*"
            alias = f'"{m_alias}"' if m_alias else f'"{m_agg}_{m_col}"'
            
            if "DISTINCT" in agg_fn:
                select_items.append(f"{agg_fn} {col_target}) AS {alias}")
            else:
                select_items.append(f"{agg_fn}({col_target}) AS {alias}")
    elif not group_by:
        select_items.append("*")

    select_clause = ", ".join(select_items) if select_items else "*"
    query = f"SELECT {select_clause} FROM {tbl}"

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if group_by:
        group_cols = ", ".join(f'"{gb}"' for gb in group_by)
        query += f" GROUP BY {group_cols}"

    if sort_by:
        order_items = []
        for s in sort_by:
            s_col = _get_val(s, "column")
            s_dir = str(_get_val(s, "direction", "desc")).upper()
            direction = "DESC" if s_dir == "DESC" else "ASC"
            order_items.append(f'"{s_col}" {direction}')
        query += " ORDER BY " + ", ".join(order_items)

    res = engine.execute_bounded_query(query, limit=limit)
    res["query"] = query
    return res, warnings
