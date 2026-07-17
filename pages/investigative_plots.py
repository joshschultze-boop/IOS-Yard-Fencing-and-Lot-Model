"""Scenario-analysis page for the yard model application."""

import matplotlib.pyplot as plt
import streamlit as st

from app_charts import (
    METRIC_LABELS,
    outer_depth_figure,
    scenario_heatmap_figure,
    scenario_scatter_figure,
)
from app_config import copy_default_inputs, scenario_count, validate_inputs
from scenario_analysis import run_scenario_grid, top_scenarios
from yard_model import calculate_model


@st.cache_data(show_spinner=False)
def cached_scenario_grid(inputs):
    """Cache the expensive grid until an input value changes."""
    return run_scenario_grid(inputs)


def display_baseline_metrics(baseline):
    """Show the selected homepage case before the broader scenario analysis."""
    st.subheader("Saved baseline case")
    column_1, column_2, column_3, column_4 = st.columns(4)

    column_1.metric("Monthly rent", f"${baseline['total_monthly_rent']:,.0f}")
    column_2.metric("Net improvement", f"${baseline['net_improvement']:,.0f}")
    column_3.metric("Leasable acres", f"{baseline['total_leasable_acres']:,.2f}")
    column_4.metric("Leasable coverage", f"{baseline['leasable_coverage']:.1%}")

    with st.expander("Baseline calculation details"):
        detail_rows = {
            "Mapped monthly rent": baseline["mapped_monthly_rent"],
            "Additional-yard monthly rent": baseline["additional_monthly_rent"],
            "Annual rent": baseline["annual_rent"],
            "Capitalized value": baseline["capitalized_value"],
            "Fencing cost": baseline["total_fencing_cost"],
            "Gate cost": baseline["total_gate_cost"],
            "Development cost after contingency": baseline[
                "total_development_cost"
            ],
        }

        for label, value in detail_rows.items():
            st.write(f"**{label}:** ${value:,.0f}")


def display_top_scenarios(results):
    """Show the ten valid cases with the highest net improvement."""
    st.subheader("Highest-value scenarios")

    columns = [
        "fill_type",
        "target_inner_yard_size_sf",
        "outer_depth_ft",
        "outer_yard_count",
        "inner_yard_count",
        "total_monthly_rent",
        "total_development_cost",
        "net_improvement",
        "leasable_coverage",
    ]
    table = top_scenarios(results)[columns].copy()
    table["fill_type"] = table["fill_type"].str.title()
    table["leasable_coverage"] = table["leasable_coverage"] * 100

    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "fill_type": "Fill type",
            "target_inner_yard_size_sf": st.column_config.NumberColumn(
                "Target inner yard (sf)", format="%.0f"
            ),
            "outer_depth_ft": st.column_config.NumberColumn(
                "Outer depth (ft)", format="%.0f"
            ),
            "outer_yard_count": "Outer yards",
            "inner_yard_count": "Inner yards",
            "total_monthly_rent": st.column_config.NumberColumn(
                "Monthly rent", format="$%.0f"
            ),
            "total_development_cost": st.column_config.NumberColumn(
                "Development cost", format="$%.0f"
            ),
            "net_improvement": st.column_config.NumberColumn(
                "Net improvement", format="$%.0f"
            ),
            "leasable_coverage": st.column_config.NumberColumn(
                "Leasable coverage", format="%.1%%"
            ),
        },
    )


def main():
    """Run the grid and render the scenario-analysis page."""
    st.set_page_config(page_title="Scenario Analysis", page_icon="📊", layout="wide")
    st.title("Scenario Analysis")
    st.caption(
        "Compare fill types, inner-yard sizes, outer-yard depths, and outer-yard counts."
    )

    if "model_inputs" in st.session_state:
        inputs = st.session_state.model_inputs
    else:
        inputs = copy_default_inputs()
        st.warning(
            "No saved homepage inputs were found. This page is using the documented "
            "default inputs."
        )

    errors = validate_inputs(inputs)
    if errors:
        st.error("The saved inputs are invalid:\n\n- " + "\n- ".join(errors))
        st.stop()

    try:
        baseline = calculate_model(inputs)
    except ValueError as error:
        st.error(f"The baseline case could not be calculated: {error}")
        st.stop()

    display_baseline_metrics(baseline)
    st.divider()

    requested_count = scenario_count(inputs)
    with st.spinner(f"Evaluating {requested_count:,} scenarios..."):
        results, failures = cached_scenario_grid(inputs)

    if results.empty:
        st.error("None of the requested scenarios produced a valid yard layout.")
        st.stop()

    column_1, column_2, column_3 = st.columns(3)
    column_1.metric("Requested scenarios", f"{requested_count:,}")
    column_2.metric("Valid scenarios", f"{len(results):,}")
    column_3.metric("Rejected layouts", f"{len(failures):,}")

    st.caption(
        "Rejected layouts are expected when a depth or yard-size combination leaves "
        "too little space to satisfy the minimum yard dimensions."
    )

    metric_name = st.selectbox(
        "Metric shown in the charts",
        options=list(METRIC_LABELS),
        format_func=lambda name: METRIC_LABELS[name],
    )

    st.subheader("All valid scenarios")
    scatter = scenario_scatter_figure(results, metric_name)
    st.pyplot(scatter, width="stretch")
    plt.close(scatter)
    st.caption("Point size represents the number of outer yards.")

    st.subheader("Outer-depth comparison")
    available_sizes = sorted(results["target_inner_yard_size_sf"].unique())
    available_counts = sorted(results["outer_yard_count"].unique())

    filter_column_1, filter_column_2 = st.columns(2)
    with filter_column_1:
        selected_inner_size = st.selectbox(
            "Target inner-yard size (sf)",
            options=available_sizes,
            format_func=lambda value: f"{value:,.0f}",
        )
    with filter_column_2:
        selected_outer_count = st.selectbox(
            "Number of outer yards",
            options=available_counts,
        )

    depth_chart = outer_depth_figure(
        results,
        metric_name,
        selected_inner_size,
        selected_outer_count,
    )
    st.pyplot(depth_chart, width="stretch")
    plt.close(depth_chart)

    st.subheader("Outer-depth and yard-count heatmap")
    filter_column_1, filter_column_2 = st.columns(2)
    with filter_column_1:
        selected_fill = st.selectbox(
            "Heatmap fill type",
            options=inputs["scenario_grid"]["fill_types"],
            format_func=str.title,
        )
    with filter_column_2:
        heatmap_inner_size = st.selectbox(
            "Heatmap target inner-yard size (sf)",
            options=available_sizes,
            format_func=lambda value: f"{value:,.0f}",
        )

    heatmap = scenario_heatmap_figure(
        results,
        metric_name,
        selected_fill,
        heatmap_inner_size,
    )
    st.pyplot(heatmap, width="stretch")
    plt.close(heatmap)

    st.divider()
    display_top_scenarios(results)

    csv_data = results.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download valid scenarios as CSV",
        data=csv_data,
        file_name="yard_model_scenarios.csv",
        mime="text/csv",
    )

    if not failures.empty:
        with st.expander("Review rejected scenarios"):
            st.dataframe(failures, hide_index=True, width="stretch")


if __name__ == "__main__":
    main()
