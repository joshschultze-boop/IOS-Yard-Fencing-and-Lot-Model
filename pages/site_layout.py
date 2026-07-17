"""Mapped site-layout page for the yard model application."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app_config import FILL_TYPES, copy_default_inputs, validate_inputs
from site_layout_chart import site_layout_figure
from yard_model import calculate_model, yard_summary_rows


def main():
    """Draw one selected fill type and show its financial summary."""
    st.set_page_config(page_title="Site Layout", page_icon="🗺️", layout="wide")
    st.title("Site Layout")
    st.caption(
        "This drawing includes the rectangular mapped lot. Additional irregular "
        "yards remain in the financial totals but are intentionally not drawn."
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

    selected_fill = st.selectbox(
        "Layout to display",
        options=FILL_TYPES,
        index=FILL_TYPES.index(inputs["layout"]["fill_type"]),
        format_func=str.title,
    )

    try:
        results = calculate_model(inputs, {"fill_type": selected_fill})
        figure, inner = site_layout_figure(inputs, selected_fill)
    except ValueError as error:
        st.error(f"This layout cannot be drawn: {error}")
        st.stop()

    column_1, column_2, column_3, column_4 = st.columns(4)
    column_1.metric("Outer yards", results["outer_yard_count"])
    column_2.metric("Inner yards", results["inner_yard_count"])
    column_3.metric(
        "Average inner-yard area",
        f"{results['inner_yard_area_acres']:.3f} acres",
    )
    column_4.metric("Leasable coverage", f"{results['leasable_coverage']:.1%}")

    st.pyplot(figure, width="stretch")
    plt.close(figure)

    additional_count = results["additional_yard_count"]
    additional_acres = results["additional_site_acres"]
    if additional_count:
        st.info(
            f"The financial totals also include {additional_count} off-map yard(s) "
            f"covering {additional_acres:,.2f} acres."
        )

    st.subheader("Yard types and assigned rents")
    yard_table = pd.DataFrame(yard_summary_rows(inputs, selected_fill))
    st.dataframe(
        yard_table,
        hide_index=True,
        width="stretch",
        column_config={
            "Yard type": "Yard type",
            "Count": "Count",
            "Average acres": st.column_config.NumberColumn(
                "Average acres", format="%.3f"
            ),
            "Rent / acre / month": st.column_config.NumberColumn(
                "Rent / acre / month", format="$%.0f"
            ),
        },
    )

    st.subheader("Selected-layout financial summary")
    column_1, column_2, column_3 = st.columns(3)
    column_1.metric("Monthly rent", f"${results['total_monthly_rent']:,.0f}")
    column_2.metric(
        "Development cost", f"${results['total_development_cost']:,.0f}"
    )
    column_3.metric("Net improvement", f"${results['net_improvement']:,.0f}")

    with st.expander("Mapped inner-area details"):
        st.write(f"**Usable inner width:** {inner['usable_width_ft']:,.1f} ft")
        st.write(f"**Usable inner height:** {inner['usable_height_ft']:,.1f} ft")
        st.write(f"**Inner yards:** {inner['yard_count']:,}")
        st.write(
            f"**Average inner-yard area:** {inner['average_yard_area_sf']:,.0f} sf"
        )


if __name__ == "__main__":
    main()
