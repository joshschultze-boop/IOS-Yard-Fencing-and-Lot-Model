"""Homepage for entering and saving yard-model assumptions."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app_charts import rent_curve_figure
from app_config import (
    ACRE_TO_SQFT,
    DEFAULT_INPUTS,
    FILL_TYPES,
    copy_default_inputs,
    effective_contingency_rate,
    scenario_count,
    slanted_side_adjustment,
    validate_inputs,
)


IRREGULAR_YARD_COLUMNS = [
    "yard_name",
    "area_acres",
    "perimeter_ft",
    "gate_count",
    "gate_length_ft",
    "rent_per_acre_override",
    "include_in_financials",
    "notes",
]


def saved_inputs_or_defaults():
    """Use saved inputs when returning to the page; otherwise use defaults."""
    if "model_inputs" in st.session_state:
        return st.session_state.model_inputs
    return copy_default_inputs()


def site_and_layout_inputs(saved_inputs):
    """Render the mapped-site and baseline-layout controls."""
    saved_site = saved_inputs["site"]
    saved_layout = saved_inputs["layout"]

    st.subheader("Main lot geometry")
    column_1, column_2 = st.columns(2)

    with column_1:
        lot_width = st.number_input(
            "Lot width (ft)",
            min_value=1.0,
            value=float(saved_site["lot_width_ft"]),
            step=1.0,
        )

    with column_2:
        lot_height = st.number_input(
            "Lot height (ft)",
            min_value=1.0,
            value=float(saved_site["lot_height_ft"]),
            step=1.0,
        )

    mapped_acres = lot_width * lot_height / ACRE_TO_SQFT
    st.caption(f"Mapped lot area: {mapped_acres:,.2f} acres")

    column_1, column_2 = st.columns(2)

    with column_1:
        slanted_side = st.number_input(
            "Slanted/effective side length (ft)",
            min_value=0.0,
            value=float(saved_site["slanted_side_length_ft"]),
            step=1.0,
            help="Enter zero to turn off the extra-perimeter allowance. This is for parallelogram lots only!",
        )

    with column_2:
        entry_distance = st.number_input(
            "Entry center distance from northeast corner (ft)",
            min_value=0.0,
            value=float(saved_site["entry_distance_from_ne_corner_ft"]),
            step=1.0,
        )

    site_inputs = {
        "lot_width_ft": lot_width,
        "lot_height_ft": lot_height,
        "slanted_side_length_ft": slanted_side,
        "entry_distance_from_ne_corner_ft": entry_distance,
    }

    st.divider()
    st.subheader("Baseline yard layout")
    column_1, column_2 = st.columns(2)

    with column_1:
        fill_type = st.selectbox(
            "Inner-yard fill type",
            options=FILL_TYPES,
            index=FILL_TYPES.index(saved_layout["fill_type"]),
            format_func=str.title,
        )

    with column_2:
        target_inner_size = st.number_input(
            "Target inner-yard size (sf)",
            min_value=1.0,
            value=float(saved_layout["target_inner_yard_size_sf"]),
            step=500.0,
        )

    st.caption(
        f"Target inner-yard size: {target_inner_size / ACRE_TO_SQFT:.3f} acres"
    )

    column_1, column_2, column_3 = st.columns(3)

    with column_1:
        outer_depth = st.number_input(
            "Outer-yard depth (ft)",
            min_value=1.0,
            value=float(saved_layout["outer_yard_depth_ft"]),
            step=5.0,
        )

    with column_2:
        outer_yard_count = st.number_input(
            "Number of outer yards",
            min_value=1,
            value=int(saved_layout["outer_yard_count"]),
            step=1,
        )

    with column_3:
        fire_lane_width = st.number_input(
            "Fire-lane width (ft)",
            min_value=1.0,
            value=float(saved_layout["fire_lane_width_ft"]),
            step=1.0,
        )

    column_1, column_2 = st.columns(2)

    with column_1:
        minimum_depth = st.number_input(
            "Minimum inner-yard depth (ft)",
            min_value=1.0,
            value=float(saved_layout["minimum_inner_yard_depth_ft"]),
            step=1.0,
        )

    with column_2:
        minimum_frontage = st.number_input(
            "Minimum inner-yard frontage (ft)",
            min_value=1.0,
            value=float(saved_layout["minimum_inner_yard_frontage_ft"]),
            step=1.0,
        )

    usable_width = lot_width - 2 * (outer_depth + fire_lane_width)
    usable_height = lot_height - 2 * (outer_depth + fire_lane_width)
    st.caption(
        "Inner rectangle before center lanes: "
        f"{max(usable_width, 0):,.0f} × {max(usable_height, 0):,.0f} ft"
    )

    layout_inputs = {
        "fill_type": fill_type,
        "target_inner_yard_size_sf": target_inner_size,
        "outer_yard_depth_ft": outer_depth,
        "outer_yard_count": outer_yard_count,
        "fire_lane_width_ft": fire_lane_width,
        "minimum_inner_yard_depth_ft": minimum_depth,
        "minimum_inner_yard_frontage_ft": minimum_frontage,
    }

    return site_inputs, layout_inputs


def cost_inputs(saved_inputs, site_inputs):
    """Render fencing, gate, contingency, and valuation controls."""
    saved_costs = saved_inputs["costs"]

    st.subheader("Development costs")
    column_1, column_2 = st.columns(2)

    with column_1:
        fence_cost = st.number_input(
            "Fence cost per linear foot ($)",
            min_value=0.0,
            value=float(saved_costs["fence_cost_per_ft"]),
            step=1.0,
        )
        outer_gate_length = st.number_input(
            "Outer gate opening (ft)",
            min_value=0.0,
            value=float(saved_costs["outer_gate_length_ft"]),
            step=1.0,
        )
        base_contingency_percent = st.number_input(
            "Base cost contingency (%)",
            min_value=0.0,
            value=float(saved_costs["base_contingency_rate"] * 100),
            step=1.0,
        )

    with column_2:
        gate_cost = st.number_input(
            "Gate cost each ($)",
            min_value=0.0,
            value=float(saved_costs["gate_cost_each"]),
            step=250.0,
        )
        inner_gate_length = st.number_input(
            "Inner gate opening (ft)",
            min_value=0.0,
            value=float(saved_costs["inner_gate_length_ft"]),
            step=1.0,
        )
        cap_rate_percent = st.number_input(
            "Capitalization rate (%)",
            min_value=0.01,
            max_value=100.0,
            value=float(saved_costs["cap_rate"] * 100),
            step=0.25,
            format="%.2f",
        )

    costs = {
        "fence_cost_per_ft": fence_cost,
        "gate_cost_each": gate_cost,
        "outer_gate_length_ft": outer_gate_length,
        "inner_gate_length_ft": inner_gate_length,
        "base_contingency_rate": base_contingency_percent / 100,
        "cap_rate": cap_rate_percent / 100,
    }

    temporary_inputs = {"site": site_inputs, "costs": costs}
    geometry_adjustment = slanted_side_adjustment(site_inputs)
    effective_rate = effective_contingency_rate(temporary_inputs)

    st.divider()
    column_1, column_2, column_3 = st.columns(3)
    column_1.metric("Base contingency", f"{costs['base_contingency_rate']:.1%}")
    column_2.metric("Slanted-side allowance", f"{geometry_adjustment:.1%}")
    column_3.metric("Effective contingency", f"{effective_rate:.1%}")

    st.caption(
        "Effective contingency equals the base contingency plus the estimated "
        "perimeter gain from the slanted side."
    )

    return costs


def rent_inputs(saved_inputs):
    """Render the rent breakpoints and the explanatory curve."""
    saved_rent = saved_inputs["rent"]

    st.subheader("Rent-per-acre breakpoints")
    st.write(
        "Small yards use the high fixed rate, large yards use the low fixed rate, "
        "and yards between the breakpoints follow the curve shown below."
    )

    column_1, column_2, column_3 = st.columns(3)

    with column_1:
        st.markdown("#### Small-yard breakpoint")
        small_size = st.number_input(
            "Small-yard breakpoint (acres)",
            min_value=0.001,
            value=float(saved_rent["small_yard_breakpoint_acres"]),
            step=0.01,
            format="%.3f",
        )
        small_rent = st.number_input(
            "Small-yard rent ($ / acre / month)",
            min_value=0.0,
            value=float(saved_rent["small_yard_rent_per_acre"]),
            step=100.0,
        )

    with column_2:
        st.markdown("#### Large-yard breakpoint")
        large_size = st.number_input(
            "Large-yard breakpoint (acres)",
            min_value=0.001,
            value=float(saved_rent["large_yard_breakpoint_acres"]),
            step=0.25,
            format="%.3f",
        )
        large_rent = st.number_input(
            "Large-yard rent ($ / acre / month)",
            min_value=0.0,
            value=float(saved_rent["large_yard_rent_per_acre"]),
            step=100.0,
        )

    with column_3:
        st.markdown("#### Scale function")
        scale_function = st.selectbox(
            "Scale function",
            options=["Linear", "Quadratic", "Exponential", "Logistic"],
            index=["Linear", "Quadratic", "Exponential", "Logistic"].index(saved_rent.get("scale_function", "Linear")),
        )
        st.markdown('###### ^ Note that the logistic function midpoint and steepness are hard-coded ^')

    rent = {
        "small_yard_breakpoint_acres": small_size,
        "small_yard_rent_per_acre": small_rent,
        "large_yard_breakpoint_acres": large_size,
        "large_yard_rent_per_acre": large_rent,
        "scale_function": scale_function,
    }

    if small_size < large_size:
        figure = rent_curve_figure(rent)
        st.pyplot(figure, width="stretch")
        plt.close(figure)

        st.caption(
            "Total monthly rent for one yard equals its acreage multiplied by the "
            "rent per acre shown above. A positive override on an additional yard "
            "replaces the curve value."
        )

    return rent


def clean_irregular_yards(editor_rows):
    """Convert the editable table into simple Python dictionaries."""
    if editor_rows.empty:
        return []

    cleaned = editor_rows.reindex(columns=IRREGULAR_YARD_COLUMNS).copy()
    cleaned["yard_name"] = cleaned["yard_name"].fillna("").astype(str).str.strip()
    cleaned["notes"] = cleaned["notes"].fillna("").astype(str).str.strip()

    numeric_columns = [
        "area_acres",
        "perimeter_ft",
        "gate_count",
        "gate_length_ft",
        "rent_per_acre_override",
    ]
    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0)

    cleaned["include_in_financials"] = (
        cleaned["include_in_financials"].fillna(True).astype(bool)
    )

    # Ignore a completely blank row created by the table's Add Row button.
    has_values = (
        cleaned["yard_name"].ne("")
        | cleaned["area_acres"].ne(0)
        | cleaned["perimeter_ft"].ne(0)
        | cleaned["notes"].ne("")
    )
    cleaned = cleaned.loc[has_values]

    yards = []
    for row in cleaned.to_dict(orient="records"):
        yards.append(
            {
                "yard_name": row["yard_name"],
                "area_acres": float(row["area_acres"]),
                "perimeter_ft": float(row["perimeter_ft"]),
                "gate_count": int(round(row["gate_count"])),
                "gate_length_ft": float(row["gate_length_ft"]),
                "rent_per_acre_override": float(row["rent_per_acre_override"]),
                "include_in_financials": bool(row["include_in_financials"]),
                "notes": row["notes"],
            }
        )

    return yards


def irregular_yard_inputs(saved_inputs):
    """Render the dynamic table for yards excluded from the rectangular map."""
    st.subheader("Additional off-map yards")
    st.write(
        "These yards affect acreage, fencing, gates, rent, and value, but they are "
        "not drawn on the rectangular site-layout page."
    )

    if "irregular_yard_table" not in st.session_state:
        st.session_state.irregular_yard_table = pd.DataFrame(
            saved_inputs["irregular_yards"],
            columns=IRREGULAR_YARD_COLUMNS,
        )

    edited_rows = st.data_editor(
        st.session_state.irregular_yard_table,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "yard_name": st.column_config.TextColumn("Yard name", required=True),
            "area_acres": st.column_config.NumberColumn(
                "Area (acres)", min_value=0.0, step=0.05, format="%.3f"
            ),
            "perimeter_ft": st.column_config.NumberColumn(
                "Perimeter (ft)", min_value=0.0, step=1.0, format="%.1f"
            ),
            "gate_count": st.column_config.NumberColumn(
                "Gates", min_value=0, step=1
            ),
            "gate_length_ft": st.column_config.NumberColumn(
                "Gate opening (ft)", min_value=0.0, step=1.0
            ),
            "rent_per_acre_override": st.column_config.NumberColumn(
                "Rent override ($ / acre / month)",
                min_value=0.0,
                step=100.0,
                help="Leave at zero to use the rent curve.",
            ),
            "include_in_financials": st.column_config.CheckboxColumn(
                "Include", default=True
            ),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )

    yards = clean_irregular_yards(edited_rows)
    included_yards = [yard for yard in yards if yard["include_in_financials"]]

    column_1, column_2, column_3 = st.columns(3)
    column_1.metric("Included additional yards", len(included_yards))
    column_2.metric(
        "Additional leasable area",
        f"{sum(yard['area_acres'] for yard in included_yards):,.2f} acres",
    )
    column_3.metric(
        "Additional gross perimeter",
        f"{sum(yard['perimeter_ft'] for yard in included_yards):,.0f} ft",
    )

    return yards


def scenario_grid_inputs(saved_inputs):
    """Render the three ranges used by the scenario-analysis page."""
    saved_grid = saved_inputs["scenario_grid"]

    st.subheader("Scenario-analysis grid")
    st.write(
        "These ranges replace the hard-coded NumPy ranges in the notebook. "
        "The plots page runs every possible combination."
    )

    fill_types = st.multiselect(
        "Fill types to compare",
        options=FILL_TYPES,
        default=saved_grid["fill_types"],
        format_func=str.title,
    )

    st.markdown("#### Inner-yard size")
    column_1, column_2, column_3 = st.columns(3)
    with column_1:
        inner_size_min = st.number_input(
            "Minimum size (sf)",
            min_value=1,
            value=int(saved_grid["inner_yard_size_min_sf"]),
            step=500,
        )
    with column_2:
        inner_size_max = st.number_input(
            "Maximum size (sf)",
            min_value=1,
            value=int(saved_grid["inner_yard_size_max_sf"]),
            step=500,
        )
    with column_3:
        inner_size_step = st.number_input(
            "Size step (sf)",
            min_value=1,
            value=int(saved_grid["inner_yard_size_step_sf"]),
            step=100,
        )

    st.markdown("#### Outer-yard depth")
    column_1, column_2, column_3 = st.columns(3)
    with column_1:
        outer_depth_min = st.number_input(
            "Minimum depth (ft)",
            min_value=1,
            value=int(saved_grid["outer_depth_min_ft"]),
            step=5,
        )
    with column_2:
        outer_depth_max = st.number_input(
            "Maximum depth (ft)",
            min_value=1,
            value=int(saved_grid["outer_depth_max_ft"]),
            step=5,
        )
    with column_3:
        outer_depth_step = st.number_input(
            "Depth step (ft)",
            min_value=1,
            value=int(saved_grid["outer_depth_step_ft"]),
            step=1,
        )

    st.markdown("#### Number of outer yards")
    column_1, column_2, column_3 = st.columns(3)
    with column_1:
        outer_count_min = st.number_input(
            "Minimum count",
            min_value=1,
            value=int(saved_grid["outer_yard_count_min"]),
            step=1,
        )
    with column_2:
        outer_count_max = st.number_input(
            "Maximum count",
            min_value=1,
            value=int(saved_grid["outer_yard_count_max"]),
            step=1,
        )
    with column_3:
        outer_count_step = st.number_input(
            "Count step",
            min_value=1,
            value=int(saved_grid["outer_yard_count_step"]),
            step=1,
        )

    grid = {
        "fill_types": fill_types,
        "inner_yard_size_min_sf": inner_size_min,
        "inner_yard_size_max_sf": inner_size_max,
        "inner_yard_size_step_sf": inner_size_step,
        "outer_depth_min_ft": outer_depth_min,
        "outer_depth_max_ft": outer_depth_max,
        "outer_depth_step_ft": outer_depth_step,
        "outer_yard_count_min": outer_count_min,
        "outer_yard_count_max": outer_count_max,
        "outer_yard_count_step": outer_count_step,
    }

    st.metric("Requested scenarios", f"{scenario_count({'scenario_grid': grid}):,}")
    return grid


def main():
    """Render the page and save one complete input dictionary."""
    st.set_page_config(page_title="Yard Model Inputs", page_icon="📐", layout="wide")

    st.title("Yard Fencing Model")
    st.caption(
        "Enter the assumptions once, save them, and use the two pages in the sidebar."
    )

    saved_inputs = saved_inputs_or_defaults()

    tabs = st.tabs(
        [
            "Site & Layout",
            "Costs & Valuation",
            "Rent curve",
            "Additional Yards",
            "Scenario Ranges",
        ]
    )

    with tabs[0]:
        site, layout = site_and_layout_inputs(saved_inputs)

    with tabs[1]:
        costs = cost_inputs(saved_inputs, site)

    with tabs[2]:
        rent = rent_inputs(saved_inputs)

    with tabs[3]:
        irregular_yards = irregular_yard_inputs(saved_inputs)

    with tabs[4]:
        scenario_grid = scenario_grid_inputs(saved_inputs)

    current_inputs = {
        "site": site,
        "layout": layout,
        "costs": costs,
        "rent": rent,
        "irregular_yards": irregular_yards,
        "scenario_grid": scenario_grid,
    }

    errors = validate_inputs(current_inputs)

    st.divider()
    st.subheader("Save model inputs")

    if errors:
        st.error("Fix these inputs before saving:\n\n- " + "\n- ".join(errors))

    if st.button(
        "Save inputs",
        type="primary",
        disabled=bool(errors),
        width="stretch",
    ):
        st.session_state.model_inputs = current_inputs
        st.session_state.irregular_yard_table = pd.DataFrame(
            irregular_yards,
            columns=IRREGULAR_YARD_COLUMNS,
        )
        st.success(
            f"Inputs saved. The plots page will evaluate "
            f"{scenario_count(current_inputs):,} scenarios."
        )

    if "model_inputs" in st.session_state:
        st.caption("Inputs are saved for the current Streamlit session.")
    else:
        st.caption("Save the inputs before opening another page.")


if __name__ == "__main__":
    main()
