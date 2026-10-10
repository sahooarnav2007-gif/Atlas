import os
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import duckdb
from atlas.config import settings

class DatasetIngestionError(Exception):
    pass

class DatasetParser:
    SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}

    @classmethod
    def validate_file(cls, filename: str, file_size: int) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise DatasetIngestionError(
                f"Unsupported file format '{ext}'. Supported formats: {', '.join(cls.SUPPORTED_EXTENSIONS)}"
            )
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if file_size > max_bytes:
            raise DatasetIngestionError(
                f"File size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed limit of {settings.max_upload_mb} MB"
            )

    @classmethod
    def load_dataframe(cls, file_path: str) -> Tuple[pd.DataFrame, List[str]]:
        path = Path(file_path)
        warnings: List[str] = []
        ext = path.suffix.lower()

        try:
            if ext in {".csv", ".tsv"}:
                sep = "\t" if ext == ".tsv" else ","
                try:
                    df = pd.read_csv(file_path, sep=sep, low_memory=False)
                except UnicodeDecodeError:
                    warnings.append("File required fallback Latin-1 decoding.")
                    df = pd.read_csv(file_path, sep=sep, encoding="latin-1", low_memory=False)
            elif ext in {".xlsx", ".xls"}:
                df = pd.read_excel(file_path)
            else:
                raise DatasetIngestionError(f"Unsupported extension: {ext}")
        except Exception as e:
            raise DatasetIngestionError(f"Failed to parse file: {str(e)}")

        if df.empty:
            raise DatasetIngestionError("Uploaded dataset is empty.")

        # Sanitize column names: remove leading/trailing whitespaces, replace weird unprintable chars
        cleaned_columns = []
        col_counts: Dict[str, int] = {}
        for col in df.columns:
            clean_name = str(col).strip()
            if not clean_name:
                clean_name = "unnamed_column"
            if clean_name in col_counts:
                col_counts[clean_name] += 1
                clean_name = f"{clean_name}_{col_counts[clean_name]}"
            else:
                col_counts[clean_name] = 0
            cleaned_columns.append(clean_name)
        
        df.columns = cleaned_columns
        return df, warnings

    @classmethod
    def infer_schema(cls, df: pd.DataFrame) -> Dict[str, Any]:
        total_rows = len(df)
        columns_info: Dict[str, Any] = {}
        candidate_identifiers: List[str] = []
        candidate_dates: List[str] = []

        for col in df.columns:
            series = df[col]
            n_unique = int(series.nunique(dropna=True))
            missing_count = int(series.isna().sum())
            missing_pct = round((missing_count / total_rows) * 100, 2) if total_rows > 0 else 0.0

            # Determine logical datatype
            inferred_type = "string"
            sample_vals = series.dropna().head(5).tolist()

            if pd.api.types.is_numeric_dtype(series):
                if pd.api.types.is_integer_dtype(series):
                    inferred_type = "integer"
                else:
                    inferred_type = "float"
            elif pd.api.types.is_bool_dtype(series):
                inferred_type = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(series):
                inferred_type = "datetime"
                candidate_dates.append(col)
            else:
                # Test if string column is actually a date/time
                if series.dropna().shape[0] > 0 and series.dtype == object:
                    try:
                        pd.to_datetime(series.dropna().head(20), errors="raise")
                        inferred_type = "datetime"
                        candidate_dates.append(col)
                    except Exception:
                        if n_unique <= 20 and n_unique < total_rows * 0.5:
                            inferred_type = "categorical"
                        else:
                            inferred_type = "string"
                else:
                    inferred_type = "categorical" if n_unique <= 20 else "string"

            # Check if candidate identifier
            if missing_count == 0 and n_unique == total_rows and total_rows > 1:
                candidate_identifiers.append(col)

            columns_info[col] = {
                "name": col,
                "inferred_type": inferred_type,
                "null_count": missing_count,
                "null_pct": missing_pct,
                "distinct_count": n_unique,
                "sample_values": [str(v) for v in sample_vals]
            }

        duplicate_rows = int(df.duplicated().sum())

        return {
            "row_count": total_rows,
            "column_count": len(df.columns),
            "duplicate_rows": duplicate_rows,
            "columns": columns_info,
            "candidate_identifiers": candidate_identifiers,
            "candidate_dates": candidate_dates,
        }
