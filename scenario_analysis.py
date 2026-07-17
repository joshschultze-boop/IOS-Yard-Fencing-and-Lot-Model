"""Run the scenario grid selected on the homepage."""

from itertools import product

import pandas as pd

from yard_model import calculate_model


def inclusive_values(minimum, maximum, step):
    """Return every integer from minimum through maximum, including maximum."""
    return list(range(minimum, maximum + 1, step))


def run_scenario_grid(inputs):
    """Run every requested combination and return successes and failures."""
    grid = inputs["scenario_grid"]

    inner_sizes = inclusive_values(
        grid["inner_yard_size_min_sf"],
        grid["inner_yard_size_max_sf"],
        grid["inner_yard_size_step_sf"],
    )
    outer_depths = inclusive_values(
        grid["outer_depth_min_ft"],
        grid["outer_depth_max_ft"],
        grid["outer_depth_step_ft"],
    )
    outer_yard_counts = inclusive_values(
        grid["outer_yard_count_min"],
        grid["outer_yard_count_max"],
        grid["outer_yard_count_step"],
    )

    successful_rows = []
    failed_rows = []

    combinations = product(
        grid["fill_types"],
        inner_sizes,
        outer_depths,
        outer_yard_counts,
    )

    for fill_type, inner_size, outer_depth, outer_yard_count in combinations:
        layout_changes = {
            "fill_type": fill_type,
            "target_inner_yard_size_sf": inner_size,
            "outer_yard_depth_ft": outer_depth,
            "outer_yard_count": outer_yard_count,
        }

        try:
            result = calculate_model(inputs, layout_changes)
            successful_rows.append(result)
        except ValueError as error:
            failed_rows.append(
                {
                    "fill_type": fill_type,
                    "target_inner_yard_size_sf": inner_size,
                    "outer_depth_ft": outer_depth,
                    "outer_yard_count": outer_yard_count,
                    "error": str(error),
                }
            )

    return pd.DataFrame(successful_rows), pd.DataFrame(failed_rows)


def top_scenarios(results, row_count=10):
    """Return the highest net-improvement cases."""
    if results.empty:
        return results.copy()

    return (
        results.sort_values("net_improvement", ascending=False)
        .head(row_count)
        .reset_index(drop=True)
    )
