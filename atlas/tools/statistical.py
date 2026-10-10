from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class StatisticalTestInput(BaseModel):
    test_type: str = Field(description="'t_test_ind', 'mann_whitney', 'chi_square', 'anova', or 'kruskal_wallis'")
    metric_column: str = Field(description="Continuous variable or first categorical variable")
    group_column: Optional[str] = Field(default=None, description="Grouping variable or second categorical variable")
    alpha: float = Field(default=0.05, description="Significance level threshold")

def compute_cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    n1, n2 = len(group1), len(group2)
    s1, s2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    if n1 + n2 <= 2:
        return 0.0
    s_pooled = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if s_pooled == 0:
        return 0.0
    return float((np.mean(group1) - np.mean(group2)) / s_pooled)

@registry.register("run_statistical_test", StatisticalTestInput)
def run_statistical_test(
    dataset_id: str,
    test_type: str,
    metric_column: str,
    group_column: Optional[str] = None,
    alpha: float = 0.05
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Supported t-tests, Mann-Whitney U, chi-square, ANOVA, and Kruskal-Wallis with assumptions and effect sizes.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []
    test_type = test_type.lower().strip()

    if metric_column not in df.columns:
        return {"error": f"Column '{metric_column}' not found."}, [f"Column {metric_column} missing."]
    if group_column and group_column not in df.columns:
        return {"error": f"Grouping column '{group_column}' not found."}, [f"Column {group_column} missing."]

    if test_type in {"t_test_ind", "mann_whitney"}:
        if not group_column:
            return {"error": "A group_column is required to compare groups."}, ["Missing group_column."]
        
        sub = df[[metric_column, group_column]].dropna()
        sub[metric_column] = pd.to_numeric(sub[metric_column], errors="coerce")
        sub = sub.dropna()
        
        groups = sub[group_column].unique()
        if len(groups) != 2:
            return {
                "error": f"Independent tests require exactly 2 distinct groups, found {len(groups)}: {list(groups)[:5]}"
            }, [f"Expected 2 groups, found {len(groups)}."]

        g1_data = sub[sub[group_column] == groups[0]][metric_column].values
        g2_data = sub[sub[group_column] == groups[1]][metric_column].values

        if len(g1_data) < 3 or len(g2_data) < 3:
            return {"error": "At least 3 observations required in each group."}, ["Insufficient observations."]

        # Check assumptions
        levene_stat, levene_p = stats.levene(g1_data, g2_data)
        equal_var = (levene_p > 0.05)

        if test_type == "t_test_ind":
            stat_res = stats.ttest_ind(g1_data, g2_data, equal_var=equal_var)
            effect_size = compute_cohens_d(g1_data, g2_data)
            effect_metric = "Cohen's d"
        else:
            stat_res = stats.mannwhitneyu(g1_data, g2_data)
            # Rank biserial correlation
            u_stat = stat_res.statistic
            effect_size = float(1 - (2 * u_stat) / (len(g1_data) * len(g2_data)))
            effect_metric = "Rank-biserial correlation"

        p_val = float(stat_res.pvalue)
        significant = p_val < alpha

        return {
            "test_type": test_type,
            "statistic": round(float(stat_res.statistic), 4),
            "p_value": round(p_val, 6),
            "alpha": alpha,
            "significant": significant,
            "effect_size": {
                "metric": effect_metric,
                "value": round(effect_size, 4)
            },
            "assumptions": {
                "equal_variance_test": "Levene",
                "levene_p_value": round(float(levene_p), 4),
                "equal_variance_met": bool(equal_var)
            },
            "group_summaries": {
                str(groups[0]): {"count": len(g1_data), "mean": round(float(np.mean(g1_data)), 3), "std": round(float(np.std(g1_data)), 3)},
                str(groups[1]): {"count": len(g2_data), "mean": round(float(np.mean(g2_data)), 3), "std": round(float(np.std(g2_data)), 3)}
            },
            "conclusion": f"Difference is {'statistically significant' if significant else 'not statistically significant'} at α={alpha}."
        }, warnings

    elif test_type in {"anova", "kruskal_wallis"}:
        if not group_column:
            return {"error": "A group_column is required for ANOVA / Kruskal-Wallis."}, ["Missing group_column."]

        sub = df[[metric_column, group_column]].dropna()
        sub[metric_column] = pd.to_numeric(sub[metric_column], errors="coerce")
        sub = sub.dropna()

        grouped_data = [group[metric_column].values for _, group in sub.groupby(group_column) if len(group) >= 2]
        if len(grouped_data) < 2:
            return {"error": "At least 2 groups with >= 2 observations required."}, ["Insufficient group data."]

        if test_type == "anova":
            stat_res = stats.f_oneway(*grouped_data)
        else:
            stat_res = stats.kruskal(*grouped_data)

        p_val = float(stat_res.pvalue)
        significant = p_val < alpha

        return {
            "test_type": test_type,
            "statistic": round(float(stat_res.statistic), 4),
            "p_value": round(p_val, 6),
            "alpha": alpha,
            "significant": significant,
            "num_groups": len(grouped_data),
            "total_samples": sum(len(g) for g in grouped_data),
            "conclusion": f"Group differences are {'statistically significant' if significant else 'not statistically significant'} at α={alpha}."
        }, warnings

    elif test_type == "chi_square":
        if not group_column:
            return {"error": "A second categorical column is required for Chi-Square test."}, ["Missing second column."]

        sub = df[[metric_column, group_column]].dropna()
        contingency_table = pd.crosstab(sub[metric_column], sub[group_column])
        chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)

        n = contingency_table.sum().sum()
        r, k = contingency_table.shape
        cramers_v = float(np.sqrt((chi2 / n) / min(r - 1, k - 1))) if min(r - 1, k - 1) > 0 else 0.0

        significant = p_val < alpha
        return {
            "test_type": "chi_square",
            "statistic": round(float(chi2), 4),
            "p_value": round(float(p_val), 6),
            "degrees_of_freedom": int(dof),
            "cramers_v_effect_size": round(cramers_v, 4),
            "contingency_shape": [int(r), int(k)],
            "significant": significant,
            "conclusion": f"Association between '{metric_column}' and '{group_column}' is {'statistically significant' if significant else 'not statistically significant'} at α={alpha}."
        }, warnings

    else:
        return {"error": f"Unsupported statistical test '{test_type}'"}, [f"Test {test_type} unsupported."]
