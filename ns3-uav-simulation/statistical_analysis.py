#!/usr/bin/env python3
"""
Statistical Significance Testing Script for O-RAN xApp Simulation Results

This script performs comprehensive statistical analysis on simulation results,
comparing Baseline vs xApp performance across multiple scenarios.

Statistical Tests:
- Paired t-test: Baseline vs xApp comparison
- One-way ANOVA: Multi-scenario comparison
- Wilcoxon signed-rank test: Non-parametric alternative
- Effect size calculation (Cohen's d)

Output:
- p-values with significance markers (*, **, ***)
- 95% confidence intervals
- LaTeX formatted statistical tables
"""

import json
import os
import glob
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Statistical libraries
from scipy import stats
from scipy.stats import ttest_rel, ttest_ind, wilcoxon, f_oneway, mannwhitneyu
from scipy.stats import shapiro, levene


@dataclass
class StatisticalResult:
    """Container for statistical test results."""
    test_name: str
    statistic: float
    p_value: float
    significance: str
    effect_size: Optional[float] = None
    effect_size_interpretation: Optional[str] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    sample_size_1: Optional[int] = None
    sample_size_2: Optional[int] = None
    mean_1: Optional[float] = None
    mean_2: Optional[float] = None
    std_1: Optional[float] = None
    std_2: Optional[float] = None


class StatisticalAnalyzer:
    """
    Statistical analysis engine for O-RAN simulation results.
    """

    # Significance level thresholds
    ALPHA_LEVELS = {
        0.001: "***",
        0.01: "**",
        0.05: "*",
        1.0: "n.s."
    }

    # Effect size interpretation (Cohen's d)
    EFFECT_SIZE_THRESHOLDS = {
        0.2: "negligible",
        0.5: "small",
        0.8: "medium",
        float('inf'): "large"
    }

    def __init__(self, results_dir: str):
        """
        Initialize the statistical analyzer.

        Args:
            results_dir: Path to the results directory
        """
        self.results_dir = Path(results_dir)
        self.scenarios_dir = self.results_dir / "scenarios"
        self.comparison_dir = self.results_dir / "comparison"
        self.statistics_dir = self.results_dir / "statistics"
        self.statistics_dir.mkdir(parents=True, exist_ok=True)

        self.scenario_data: Dict[str, Dict] = {}
        self.comparison_data: List[Dict] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_data(self) -> bool:
        """
        Load data from scenario and comparison result files.

        Returns:
            True if data was loaded successfully
        """
        print("=" * 60)
        print("Loading Statistical Analysis Data")
        print("=" * 60)

        # Load scenario data
        scenario_files = list(self.scenarios_dir.glob("*.json"))
        if not scenario_files:
            print(f"[WARNING] No scenario files found in {self.scenarios_dir}")
        else:
            for file_path in scenario_files:
                if "comparison_summary" in file_path.name:
                    continue
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        scenario_name = data.get("scenario_name", file_path.stem)
                        self.scenario_data[scenario_name] = data
                        print(f"[LOADED] Scenario: {scenario_name} ({len(data.get('decisions', []))} samples)")
                except Exception as e:
                    print(f"[ERROR] Failed to load {file_path}: {e}")

        # Load comparison data
        comparison_files = sorted(self.comparison_dir.glob("comparison_results_*.json"))
        if not comparison_files:
            print(f"[WARNING] No comparison files found in {self.comparison_dir}")
        else:
            for file_path in comparison_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        self.comparison_data.append(data)
                        print(f"[LOADED] Comparison: {file_path.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to load {file_path}: {e}")

        total_loaded = len(self.scenario_data) + len(self.comparison_data)
        print(f"\nTotal files loaded: {total_loaded}")
        return total_loaded > 0

    def get_significance_marker(self, p_value: float) -> str:
        """
        Get significance marker based on p-value.

        Args:
            p_value: The p-value from statistical test

        Returns:
            Significance marker (*, **, ***, or n.s.)
        """
        for threshold, marker in sorted(self.ALPHA_LEVELS.items()):
            if p_value < threshold:
                return marker
        return "n.s."

    def interpret_effect_size(self, d: float) -> str:
        """
        Interpret Cohen's d effect size.

        Args:
            d: Cohen's d value

        Returns:
            Interpretation string
        """
        d_abs = abs(d)
        for threshold, interpretation in sorted(self.EFFECT_SIZE_THRESHOLDS.items()):
            if d_abs < threshold:
                return interpretation
        return "large"

    def cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """
        Calculate Cohen's d effect size for two groups.

        Args:
            group1: First group data
            group2: Second group data

        Returns:
            Cohen's d value
        """
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        return (np.mean(group1) - np.mean(group2)) / pooled_std

    def confidence_interval(self, data: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for data.

        Args:
            data: Input data array
            confidence: Confidence level (default 0.95 for 95% CI)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        n = len(data)
        mean = np.mean(data)
        se = stats.sem(data)
        h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
        return mean - h, mean + h

    def extract_metric_samples(self, scenario_data: Dict, metric: str) -> np.ndarray:
        """
        Extract metric samples from scenario data.

        Args:
            scenario_data: Scenario data dictionary
            metric: Metric name (rsrp, sinr, etc.)

        Returns:
            NumPy array of metric values
        """
        decisions = scenario_data.get("decisions", [])
        if not decisions:
            return np.array([])

        values = []
        for decision in decisions:
            if metric in decision:
                values.append(decision[metric])
        return np.array(values)

    def paired_ttest(self, baseline: np.ndarray, xapp: np.ndarray,
                     metric_name: str = "metric") -> StatisticalResult:
        """
        Perform paired t-test between baseline and xApp results.

        Args:
            baseline: Baseline data
            xapp: xApp data
            metric_name: Name of the metric being tested

        Returns:
            StatisticalResult object
        """
        # Ensure equal sample sizes for paired test
        min_len = min(len(baseline), len(xapp))
        baseline = baseline[:min_len]
        xapp = xapp[:min_len]

        if min_len < 2:
            return StatisticalResult(
                test_name=f"Paired t-test ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance="n.s. (insufficient data)"
            )

        statistic, p_value = ttest_rel(baseline, xapp)
        effect_size = self.cohens_d(baseline, xapp)
        ci_lower, ci_upper = self.confidence_interval(baseline - xapp)

        return StatisticalResult(
            test_name=f"Paired t-test ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            significance=self.get_significance_marker(p_value),
            effect_size=effect_size,
            effect_size_interpretation=self.interpret_effect_size(effect_size),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            sample_size_1=len(baseline),
            sample_size_2=len(xapp),
            mean_1=np.mean(baseline),
            mean_2=np.mean(xapp),
            std_1=np.std(baseline),
            std_2=np.std(xapp)
        )

    def independent_ttest(self, group1: np.ndarray, group2: np.ndarray,
                          metric_name: str = "metric") -> StatisticalResult:
        """
        Perform independent samples t-test.

        Args:
            group1: First group data
            group2: Second group data
            metric_name: Name of the metric being tested

        Returns:
            StatisticalResult object
        """
        if len(group1) < 2 or len(group2) < 2:
            return StatisticalResult(
                test_name=f"Independent t-test ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance="n.s. (insufficient data)"
            )

        statistic, p_value = ttest_ind(group1, group2)
        effect_size = self.cohens_d(group1, group2)
        ci1 = self.confidence_interval(group1)
        ci2 = self.confidence_interval(group2)

        return StatisticalResult(
            test_name=f"Independent t-test ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            significance=self.get_significance_marker(p_value),
            effect_size=effect_size,
            effect_size_interpretation=self.interpret_effect_size(effect_size),
            ci_lower=ci1[0],
            ci_upper=ci1[1],
            sample_size_1=len(group1),
            sample_size_2=len(group2),
            mean_1=np.mean(group1),
            mean_2=np.mean(group2),
            std_1=np.std(group1),
            std_2=np.std(group2)
        )

    def wilcoxon_test(self, baseline: np.ndarray, xapp: np.ndarray,
                      metric_name: str = "metric") -> StatisticalResult:
        """
        Perform Wilcoxon signed-rank test (non-parametric alternative to paired t-test).

        Args:
            baseline: Baseline data
            xapp: xApp data
            metric_name: Name of the metric being tested

        Returns:
            StatisticalResult object
        """
        min_len = min(len(baseline), len(xapp))
        baseline = baseline[:min_len]
        xapp = xapp[:min_len]

        if min_len < 10:
            return StatisticalResult(
                test_name=f"Wilcoxon signed-rank ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance="n.s. (insufficient data, n<10)"
            )

        # Handle case where differences are all zero
        diff = baseline - xapp
        if np.all(diff == 0):
            return StatisticalResult(
                test_name=f"Wilcoxon signed-rank ({metric_name})",
                statistic=0.0,
                p_value=1.0,
                significance="n.s. (no difference)"
            )

        try:
            statistic, p_value = wilcoxon(baseline, xapp, alternative='two-sided')
        except ValueError as e:
            return StatisticalResult(
                test_name=f"Wilcoxon signed-rank ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance=f"n.s. ({str(e)})"
            )

        # Calculate rank-biserial correlation as effect size
        n = len(diff[diff != 0])
        r = 1 - (2 * statistic) / (n * (n + 1))

        return StatisticalResult(
            test_name=f"Wilcoxon signed-rank ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            significance=self.get_significance_marker(p_value),
            effect_size=r,
            effect_size_interpretation=self.interpret_effect_size(r),
            sample_size_1=len(baseline),
            sample_size_2=len(xapp),
            mean_1=np.median(baseline),
            mean_2=np.median(xapp)
        )

    def mann_whitney_test(self, group1: np.ndarray, group2: np.ndarray,
                          metric_name: str = "metric") -> StatisticalResult:
        """
        Perform Mann-Whitney U test (non-parametric alternative to independent t-test).

        Args:
            group1: First group data
            group2: Second group data
            metric_name: Name of the metric being tested

        Returns:
            StatisticalResult object
        """
        if len(group1) < 2 or len(group2) < 2:
            return StatisticalResult(
                test_name=f"Mann-Whitney U ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance="n.s. (insufficient data)"
            )

        statistic, p_value = mannwhitneyu(group1, group2, alternative='two-sided')

        # Calculate effect size (rank-biserial correlation)
        n1, n2 = len(group1), len(group2)
        r = 1 - (2 * statistic) / (n1 * n2)

        return StatisticalResult(
            test_name=f"Mann-Whitney U ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            significance=self.get_significance_marker(p_value),
            effect_size=r,
            effect_size_interpretation=self.interpret_effect_size(r),
            sample_size_1=n1,
            sample_size_2=n2,
            mean_1=np.median(group1),
            mean_2=np.median(group2)
        )

    def one_way_anova(self, groups: Dict[str, np.ndarray],
                      metric_name: str = "metric") -> StatisticalResult:
        """
        Perform one-way ANOVA for multi-scenario comparison.

        Args:
            groups: Dictionary mapping group names to data arrays
            metric_name: Name of the metric being tested

        Returns:
            StatisticalResult object
        """
        group_list = list(groups.values())
        group_names = list(groups.keys())

        # Filter out groups with insufficient data
        valid_groups = [(name, data) for name, data in zip(group_names, group_list)
                        if len(data) >= 2]

        if len(valid_groups) < 2:
            return StatisticalResult(
                test_name=f"One-way ANOVA ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance="n.s. (insufficient groups)"
            )

        group_names, group_list = zip(*valid_groups)
        statistic, p_value = f_oneway(*group_list)

        # Calculate eta-squared effect size
        # eta^2 = SS_between / SS_total
        all_data = np.concatenate(group_list)
        grand_mean = np.mean(all_data)
        ss_total = np.sum((all_data - grand_mean) ** 2)
        ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in group_list)
        eta_squared = ss_between / ss_total if ss_total > 0 else 0

        return StatisticalResult(
            test_name=f"One-way ANOVA ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            significance=self.get_significance_marker(p_value),
            effect_size=eta_squared,
            effect_size_interpretation=f"eta^2={eta_squared:.4f}",
            sample_size_1=sum(len(g) for g in group_list),
            sample_size_2=len(group_list)
        )

    def kruskal_wallis_test(self, groups: Dict[str, np.ndarray],
                            metric_name: str = "metric") -> StatisticalResult:
        """
        Perform Kruskal-Wallis H test (non-parametric alternative to one-way ANOVA).

        Args:
            groups: Dictionary mapping group names to data arrays
            metric_name: Name of the metric being tested

        Returns:
            StatisticalResult object
        """
        group_list = list(groups.values())
        group_names = list(groups.keys())

        # Filter out groups with insufficient data
        valid_groups = [(name, data) for name, data in zip(group_names, group_list)
                        if len(data) >= 2]

        if len(valid_groups) < 2:
            return StatisticalResult(
                test_name=f"Kruskal-Wallis H ({metric_name})",
                statistic=np.nan,
                p_value=1.0,
                significance="n.s. (insufficient groups)"
            )

        group_names, group_list = zip(*valid_groups)
        statistic, p_value = stats.kruskal(*group_list)

        # Calculate epsilon-squared effect size
        n = sum(len(g) for g in group_list)
        k = len(group_list)
        epsilon_squared = (statistic - k + 1) / (n - k) if n > k else 0

        return StatisticalResult(
            test_name=f"Kruskal-Wallis H ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            significance=self.get_significance_marker(p_value),
            effect_size=epsilon_squared,
            effect_size_interpretation=f"epsilon^2={epsilon_squared:.4f}",
            sample_size_1=n,
            sample_size_2=k
        )

    def normality_test(self, data: np.ndarray, name: str = "data") -> Tuple[float, float, bool]:
        """
        Test for normality using Shapiro-Wilk test.

        Args:
            data: Input data array
            name: Name for the data

        Returns:
            Tuple of (statistic, p_value, is_normal)
        """
        if len(data) < 3:
            return np.nan, 1.0, False

        # Shapiro-Wilk test (for samples < 5000)
        if len(data) > 5000:
            data = np.random.choice(data, 5000, replace=False)

        statistic, p_value = shapiro(data)
        is_normal = p_value > 0.05
        return statistic, p_value, is_normal

    def homogeneity_of_variance_test(self, *groups) -> Tuple[float, float, bool]:
        """
        Test for homogeneity of variance using Levene's test.

        Args:
            *groups: Variable number of data arrays

        Returns:
            Tuple of (statistic, p_value, is_homogeneous)
        """
        valid_groups = [g for g in groups if len(g) >= 2]
        if len(valid_groups) < 2:
            return np.nan, 1.0, False

        statistic, p_value = levene(*valid_groups)
        is_homogeneous = p_value > 0.05
        return statistic, p_value, is_homogeneous

    def run_baseline_vs_xapp_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive statistical analysis comparing baseline vs xApp.

        Returns:
            Dictionary containing all analysis results
        """
        print("\n" + "=" * 60)
        print("Baseline vs xApp Statistical Analysis")
        print("=" * 60)

        results = {
            "timestamp": self.timestamp,
            "analysis_type": "baseline_vs_xapp",
            "tests": [],
            "metrics_summary": {},
            "assumptions_tests": []
        }

        if not self.comparison_data:
            print("[WARNING] No comparison data available")
            return results

        # Aggregate data from all comparison runs
        baseline_throughput = []
        xapp_throughput = []
        baseline_rsrp = []
        xapp_rsrp = []
        baseline_sinr = []
        xapp_sinr = []
        baseline_delay = []
        xapp_delay = []

        for comp in self.comparison_data:
            base = comp.get("baseline_summary", {})
            xapp = comp.get("xapp_summary", {})

            if base.get("avg_throughput_mbps"):
                baseline_throughput.append(base["avg_throughput_mbps"])
            if xapp.get("avg_throughput_mbps"):
                xapp_throughput.append(xapp["avg_throughput_mbps"])
            if base.get("avg_rsrp"):
                baseline_rsrp.append(base["avg_rsrp"])
            if xapp.get("avg_rsrp"):
                xapp_rsrp.append(xapp["avg_rsrp"])
            if base.get("avg_sinr"):
                baseline_sinr.append(base["avg_sinr"])
            if xapp.get("avg_sinr"):
                xapp_sinr.append(xapp["avg_sinr"])
            if base.get("total_handover_delay_ms"):
                baseline_delay.append(base["total_handover_delay_ms"])
            if xapp.get("total_handover_delay_ms"):
                xapp_delay.append(xapp["total_handover_delay_ms"])

        # Convert to numpy arrays
        baseline_throughput = np.array(baseline_throughput)
        xapp_throughput = np.array(xapp_throughput)
        baseline_rsrp = np.array(baseline_rsrp)
        xapp_rsrp = np.array(xapp_rsrp)
        baseline_sinr = np.array(baseline_sinr)
        xapp_sinr = np.array(xapp_sinr)
        baseline_delay = np.array(baseline_delay)
        xapp_delay = np.array(xapp_delay)

        # Also extract sample-level data from scenarios
        baseline_rsrp_samples = np.array([])
        xapp_rsrp_samples = np.array([])
        baseline_sinr_samples = np.array([])
        xapp_sinr_samples = np.array([])

        if "baseline" in self.scenario_data:
            baseline_rsrp_samples = self.extract_metric_samples(self.scenario_data["baseline"], "rsrp")
            baseline_sinr_samples = self.extract_metric_samples(self.scenario_data["baseline"], "sinr")

        # Use high_load or fast_uav as xApp proxy (same underlying data with xApp control)
        for scenario_name in ["high_load", "fast_uav", "slow_uav"]:
            if scenario_name in self.scenario_data:
                xapp_rsrp_samples = self.extract_metric_samples(self.scenario_data[scenario_name], "rsrp")
                xapp_sinr_samples = self.extract_metric_samples(self.scenario_data[scenario_name], "sinr")
                break

        # Run statistical tests
        metrics_to_test = [
            ("Throughput", baseline_throughput, xapp_throughput),
            ("RSRP", baseline_rsrp, xapp_rsrp),
            ("SINR", baseline_sinr, xapp_sinr),
            ("Handover Delay", baseline_delay, xapp_delay),
        ]

        print("\n--- Parametric Tests ---")
        for metric_name, baseline, xapp in metrics_to_test:
            if len(baseline) >= 2 and len(xapp) >= 2:
                # Paired t-test
                result = self.paired_ttest(baseline, xapp, metric_name)
                results["tests"].append(self._result_to_dict(result))
                self._print_result(result)

                # Store metrics summary
                results["metrics_summary"][metric_name] = {
                    "baseline_mean": float(np.mean(baseline)) if len(baseline) > 0 else None,
                    "baseline_std": float(np.std(baseline)) if len(baseline) > 0 else None,
                    "baseline_ci": list(self.confidence_interval(baseline)) if len(baseline) > 1 else None,
                    "xapp_mean": float(np.mean(xapp)) if len(xapp) > 0 else None,
                    "xapp_std": float(np.std(xapp)) if len(xapp) > 0 else None,
                    "xapp_ci": list(self.confidence_interval(xapp)) if len(xapp) > 1 else None,
                }
            else:
                print(f"[SKIP] {metric_name}: Insufficient data (baseline={len(baseline)}, xapp={len(xapp)})")

        print("\n--- Non-Parametric Tests ---")
        for metric_name, baseline, xapp in metrics_to_test:
            if len(baseline) >= 10 and len(xapp) >= 10:
                result = self.wilcoxon_test(baseline, xapp, metric_name)
                results["tests"].append(self._result_to_dict(result))
                self._print_result(result)
            else:
                print(f"[SKIP] {metric_name}: Insufficient data for Wilcoxon (need n>=10)")

        # Sample-level analysis (using scenario data)
        print("\n--- Sample-Level Analysis ---")
        if len(baseline_rsrp_samples) >= 2 and len(xapp_rsrp_samples) >= 2:
            result = self.independent_ttest(baseline_rsrp_samples, xapp_rsrp_samples, "RSRP (samples)")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

            result = self.mann_whitney_test(baseline_rsrp_samples, xapp_rsrp_samples, "RSRP (samples)")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

        if len(baseline_sinr_samples) >= 2 and len(xapp_sinr_samples) >= 2:
            result = self.independent_ttest(baseline_sinr_samples, xapp_sinr_samples, "SINR (samples)")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

        # Normality tests for assumptions checking
        print("\n--- Assumption Tests ---")
        for metric_name, baseline, xapp in metrics_to_test:
            if len(baseline) >= 3:
                stat, p, is_normal = self.normality_test(baseline, f"Baseline {metric_name}")
                results["assumptions_tests"].append({
                    "test": "Shapiro-Wilk",
                    "data": f"Baseline {metric_name}",
                    "statistic": float(stat) if not np.isnan(stat) else None,
                    "p_value": float(p),
                    "is_normal": is_normal
                })
                print(f"Normality (Baseline {metric_name}): W={stat:.4f}, p={p:.4f} {'[Normal]' if is_normal else '[Non-normal]'}")

            if len(xapp) >= 3:
                stat, p, is_normal = self.normality_test(xapp, f"xApp {metric_name}")
                results["assumptions_tests"].append({
                    "test": "Shapiro-Wilk",
                    "data": f"xApp {metric_name}",
                    "statistic": float(stat) if not np.isnan(stat) else None,
                    "p_value": float(p),
                    "is_normal": is_normal
                })
                print(f"Normality (xApp {metric_name}): W={stat:.4f}, p={p:.4f} {'[Normal]' if is_normal else '[Non-normal]'}")

        return results

    def run_multi_scenario_analysis(self) -> Dict[str, Any]:
        """
        Run multi-scenario comparison using ANOVA and Kruskal-Wallis.

        Returns:
            Dictionary containing all analysis results
        """
        print("\n" + "=" * 60)
        print("Multi-Scenario Statistical Analysis")
        print("=" * 60)

        results = {
            "timestamp": self.timestamp,
            "analysis_type": "multi_scenario",
            "scenarios": list(self.scenario_data.keys()),
            "tests": [],
            "pairwise_comparisons": []
        }

        if len(self.scenario_data) < 2:
            print("[WARNING] Need at least 2 scenarios for comparison")
            return results

        # Extract metrics for each scenario
        rsrp_groups = {}
        sinr_groups = {}

        for scenario_name, data in self.scenario_data.items():
            rsrp = self.extract_metric_samples(data, "rsrp")
            sinr = self.extract_metric_samples(data, "sinr")

            if len(rsrp) > 0:
                rsrp_groups[scenario_name] = rsrp
            if len(sinr) > 0:
                sinr_groups[scenario_name] = sinr

            print(f"Scenario '{scenario_name}': {len(rsrp)} RSRP samples, {len(sinr)} SINR samples")

        # One-way ANOVA
        print("\n--- One-way ANOVA ---")
        if len(rsrp_groups) >= 2:
            result = self.one_way_anova(rsrp_groups, "RSRP")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

        if len(sinr_groups) >= 2:
            result = self.one_way_anova(sinr_groups, "SINR")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

        # Kruskal-Wallis (non-parametric alternative)
        print("\n--- Kruskal-Wallis H Test ---")
        if len(rsrp_groups) >= 2:
            result = self.kruskal_wallis_test(rsrp_groups, "RSRP")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

        if len(sinr_groups) >= 2:
            result = self.kruskal_wallis_test(sinr_groups, "SINR")
            results["tests"].append(self._result_to_dict(result))
            self._print_result(result)

        # Pairwise comparisons (post-hoc)
        print("\n--- Pairwise Comparisons (Post-hoc) ---")
        scenario_names = list(rsrp_groups.keys())
        for i in range(len(scenario_names)):
            for j in range(i + 1, len(scenario_names)):
                name1, name2 = scenario_names[i], scenario_names[j]
                rsrp1, rsrp2 = rsrp_groups[name1], rsrp_groups[name2]

                result = self.independent_ttest(rsrp1, rsrp2, f"RSRP: {name1} vs {name2}")
                results["pairwise_comparisons"].append({
                    "comparison": f"{name1} vs {name2}",
                    "metric": "RSRP",
                    **self._result_to_dict(result)
                })
                print(f"  {name1} vs {name2} (RSRP): t={result.statistic:.4f}, p={result.p_value:.4f} {result.significance}")

        return results

    def generate_latex_table(self, results: Dict[str, Any]) -> str:
        """
        Generate LaTeX formatted table from results.

        Args:
            results: Analysis results dictionary

        Returns:
            LaTeX table string
        """
        latex = []
        latex.append("% Statistical Analysis Results")
        latex.append(f"% Generated: {self.timestamp}")
        latex.append("")

        # Main results table
        latex.append("\\begin{table}[htbp]")
        latex.append("\\centering")
        latex.append("\\caption{Statistical Significance Test Results}")
        latex.append("\\label{tab:statistical_results}")
        latex.append("\\begin{tabular}{lcccccc}")
        latex.append("\\toprule")
        latex.append("Test & Statistic & p-value & Sig. & Effect Size & CI (95\\%) \\\\")
        latex.append("\\midrule")

        for test in results.get("tests", []):
            test_name = test.get("test_name", "N/A")
            statistic = test.get("statistic")
            p_value = test.get("p_value")
            sig = test.get("significance", "n.s.")
            effect_size = test.get("effect_size")
            ci_lower = test.get("ci_lower")
            ci_upper = test.get("ci_upper")

            # Helper function to check if value is valid number
            def is_valid_num(x):
                if x is None:
                    return False
                try:
                    return not np.isnan(float(x)) and not np.isinf(float(x))
                except (TypeError, ValueError):
                    return False

            # Format values
            stat_str = f"{statistic:.3f}" if is_valid_num(statistic) else "N/A"
            p_str = f"{p_value:.4f}" if is_valid_num(p_value) else "N/A"
            if is_valid_num(p_value) and p_value < 0.001:
                p_str = "$<$0.001"
            es_str = f"{effect_size:.3f}" if is_valid_num(effect_size) else "N/A"

            if is_valid_num(ci_lower) and is_valid_num(ci_upper):
                ci_str = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
            else:
                ci_str = "N/A"

            # Escape underscores for LaTeX
            test_name = test_name.replace("_", "\\_")

            latex.append(f"{test_name} & {stat_str} & {p_str} & {sig} & {es_str} & {ci_str} \\\\")

        latex.append("\\bottomrule")
        latex.append("\\end{tabular}")
        latex.append("\\begin{tablenotes}")
        latex.append("\\small")
        latex.append("\\item Note: * p $<$ 0.05, ** p $<$ 0.01, *** p $<$ 0.001, n.s. = not significant")
        latex.append("\\item Effect size: Cohen's d (small: 0.2, medium: 0.5, large: 0.8)")
        latex.append("\\end{tablenotes}")
        latex.append("\\end{table}")
        latex.append("")

        # Metrics summary table
        if "metrics_summary" in results and results["metrics_summary"]:
            latex.append("\\begin{table}[htbp]")
            latex.append("\\centering")
            latex.append("\\caption{Descriptive Statistics Summary}")
            latex.append("\\label{tab:descriptive_stats}")
            latex.append("\\begin{tabular}{lccccc}")
            latex.append("\\toprule")
            latex.append("Metric & \\multicolumn{2}{c}{Baseline} & \\multicolumn{2}{c}{xApp} & Improvement \\\\")
            latex.append("\\cmidrule(lr){2-3} \\cmidrule(lr){4-5}")
            latex.append(" & Mean $\\pm$ SD & 95\\% CI & Mean $\\pm$ SD & 95\\% CI & (\\%) \\\\")
            latex.append("\\midrule")

            for metric_name, stats in results["metrics_summary"].items():
                b_mean = stats.get("baseline_mean")
                b_std = stats.get("baseline_std")
                b_ci = stats.get("baseline_ci")
                x_mean = stats.get("xapp_mean")
                x_std = stats.get("xapp_std")
                x_ci = stats.get("xapp_ci")

                if b_mean is not None and x_mean is not None:
                    improvement = ((x_mean - b_mean) / abs(b_mean)) * 100 if b_mean != 0 else 0

                    b_str = f"{b_mean:.2f} $\\pm$ {b_std:.2f}" if b_std else f"{b_mean:.2f}"
                    x_str = f"{x_mean:.2f} $\\pm$ {x_std:.2f}" if x_std else f"{x_mean:.2f}"
                    b_ci_str = f"[{b_ci[0]:.2f}, {b_ci[1]:.2f}]" if b_ci else "N/A"
                    x_ci_str = f"[{x_ci[0]:.2f}, {x_ci[1]:.2f}]" if x_ci else "N/A"
                    imp_str = f"{improvement:+.1f}\\%"

                    metric_name = metric_name.replace("_", "\\_")
                    latex.append(f"{metric_name} & {b_str} & {b_ci_str} & {x_str} & {x_ci_str} & {imp_str} \\\\")

            latex.append("\\bottomrule")
            latex.append("\\end{tabular}")
            latex.append("\\end{table}")

        return "\n".join(latex)

    def _result_to_dict(self, result: StatisticalResult) -> Dict:
        """Convert StatisticalResult to dictionary."""
        return {
            "test_name": result.test_name,
            "statistic": float(result.statistic) if not np.isnan(result.statistic) else None,
            "p_value": float(result.p_value) if not np.isnan(result.p_value) else None,
            "significance": result.significance,
            "effect_size": float(result.effect_size) if result.effect_size is not None and not np.isnan(result.effect_size) else None,
            "effect_size_interpretation": result.effect_size_interpretation,
            "ci_lower": float(result.ci_lower) if result.ci_lower is not None and not np.isnan(result.ci_lower) else None,
            "ci_upper": float(result.ci_upper) if result.ci_upper is not None and not np.isnan(result.ci_upper) else None,
            "sample_size_1": result.sample_size_1,
            "sample_size_2": result.sample_size_2,
            "mean_1": float(result.mean_1) if result.mean_1 is not None and not np.isnan(result.mean_1) else None,
            "mean_2": float(result.mean_2) if result.mean_2 is not None and not np.isnan(result.mean_2) else None,
            "std_1": float(result.std_1) if result.std_1 is not None and not np.isnan(result.std_1) else None,
            "std_2": float(result.std_2) if result.std_2 is not None and not np.isnan(result.std_2) else None,
        }

    def _print_result(self, result: StatisticalResult) -> None:
        """Print formatted statistical result."""
        stat_str = f"{result.statistic:.4f}" if not np.isnan(result.statistic) else "N/A"
        p_str = f"{result.p_value:.6f}" if not np.isnan(result.p_value) else "N/A"
        es_str = f"{result.effect_size:.4f}" if result.effect_size is not None and not np.isnan(result.effect_size) else "N/A"

        print(f"\n{result.test_name}")
        print(f"  Statistic: {stat_str}")
        print(f"  p-value: {p_str} {result.significance}")
        print(f"  Effect size: {es_str} ({result.effect_size_interpretation})" if result.effect_size_interpretation else f"  Effect size: {es_str}")

        if result.ci_lower is not None and result.ci_upper is not None:
            print(f"  95% CI: [{result.ci_lower:.4f}, {result.ci_upper:.4f}]")

        if result.mean_1 is not None and result.mean_2 is not None:
            print(f"  Group 1: mean={result.mean_1:.4f}, n={result.sample_size_1}")
            print(f"  Group 2: mean={result.mean_2:.4f}, n={result.sample_size_2}")

    def save_results(self, results: Dict[str, Any], analysis_type: str) -> str:
        """
        Save analysis results to files.

        Args:
            results: Analysis results dictionary
            analysis_type: Type of analysis (for filename)

        Returns:
            Path to saved JSON file
        """
        # Save JSON results
        json_path = self.statistics_dir / f"{analysis_type}_{self.timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n[SAVED] JSON: {json_path}")

        # Generate and save LaTeX table
        latex_content = self.generate_latex_table(results)
        latex_path = self.statistics_dir / f"{analysis_type}_{self.timestamp}.tex"
        with open(latex_path, 'w') as f:
            f.write(latex_content)
        print(f"[SAVED] LaTeX: {latex_path}")

        return str(json_path)

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run complete statistical analysis pipeline.

        Returns:
            Combined results dictionary
        """
        print("\n" + "=" * 60)
        print("Statistical Significance Analysis")
        print("=" * 60)
        print(f"Timestamp: {self.timestamp}")
        print(f"Results directory: {self.results_dir}")

        # Load data
        if not self.load_data():
            print("[ERROR] No data loaded. Exiting.")
            return {}

        # Run analyses
        baseline_vs_xapp_results = self.run_baseline_vs_xapp_analysis()
        multi_scenario_results = self.run_multi_scenario_analysis()

        # Save results
        if baseline_vs_xapp_results.get("tests"):
            self.save_results(baseline_vs_xapp_results, "baseline_vs_xapp")

        if multi_scenario_results.get("tests"):
            self.save_results(multi_scenario_results, "multi_scenario")

        # Generate summary report
        summary = self.generate_summary_report(baseline_vs_xapp_results, multi_scenario_results)

        return {
            "timestamp": self.timestamp,
            "baseline_vs_xapp": baseline_vs_xapp_results,
            "multi_scenario": multi_scenario_results,
            "summary": summary
        }

    def generate_summary_report(self, baseline_results: Dict, scenario_results: Dict) -> Dict:
        """
        Generate a summary report of all statistical tests.

        Args:
            baseline_results: Baseline vs xApp results
            scenario_results: Multi-scenario results

        Returns:
            Summary dictionary
        """
        print("\n" + "=" * 60)
        print("Summary Report")
        print("=" * 60)

        summary = {
            "total_tests": 0,
            "significant_tests": 0,
            "highly_significant_tests": 0,
            "key_findings": []
        }

        all_tests = baseline_results.get("tests", []) + scenario_results.get("tests", [])
        summary["total_tests"] = len(all_tests)

        for test in all_tests:
            sig = test.get("significance", "n.s.")
            if sig in ["*", "**", "***"]:
                summary["significant_tests"] += 1
                if sig in ["**", "***"]:
                    summary["highly_significant_tests"] += 1

                finding = {
                    "test": test["test_name"],
                    "p_value": test["p_value"],
                    "significance": sig,
                    "effect_size": test.get("effect_size")
                }
                summary["key_findings"].append(finding)

        print(f"\nTotal tests performed: {summary['total_tests']}")
        print(f"Significant results (p < 0.05): {summary['significant_tests']}")
        print(f"Highly significant (p < 0.01): {summary['highly_significant_tests']}")

        if summary["key_findings"]:
            print("\nKey Findings:")
            for finding in summary["key_findings"]:
                print(f"  - {finding['test']}: p={finding['p_value']:.6f} {finding['significance']}")

        # Save summary report
        summary_path = self.statistics_dir / f"summary_report_{self.timestamp}.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n[SAVED] Summary: {summary_path}")

        return summary


def main():
    """Main entry point for statistical analysis."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Statistical Significance Testing for O-RAN xApp Simulation"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results",
        help="Path to results directory"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Determine results directory path
    script_dir = Path(__file__).parent.absolute()
    results_dir = script_dir / args.results_dir

    if not results_dir.exists():
        print(f"[ERROR] Results directory not found: {results_dir}")
        return 1

    # Run analysis
    analyzer = StatisticalAnalyzer(str(results_dir))
    results = analyzer.run_full_analysis()

    # Print final p-values summary
    print("\n" + "=" * 60)
    print("P-Values Summary")
    print("=" * 60)

    all_tests = (results.get("baseline_vs_xapp", {}).get("tests", []) +
                 results.get("multi_scenario", {}).get("tests", []))

    if all_tests:
        print(f"{'Test':<50} {'p-value':<12} {'Sig.':<6}")
        print("-" * 68)
        for test in all_tests:
            name = test.get("test_name", "N/A")[:48]
            p_val = test.get("p_value")
            sig = test.get("significance", "n.s.")
            p_str = f"{p_val:.6f}" if p_val is not None else "N/A"
            print(f"{name:<50} {p_str:<12} {sig:<6}")
    else:
        print("No statistical tests were performed (insufficient data).")

    return 0


if __name__ == "__main__":
    exit(main())
