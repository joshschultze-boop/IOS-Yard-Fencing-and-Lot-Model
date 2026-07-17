"""Matplotlib charts used by the homepage and scenario-analysis page."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, PercentFormatter

from yard_model import rent_per_acre


FILL_COLORS = {
    "full": "#2F6B9A",
    "line": "#2E8B57",
    "cross": "#D97724",
}

METRIC_LABELS = {
    "net_improvement": "Net Improvement",
    "total_monthly_rent": "Total Monthly Rent",
    "total_development_cost": "Total Development Cost",
    "total_leasable_acres": "Total Leasable Acres",
    "leasable_coverage": "Leasable Coverage",
}


def format_metric_axis(axis, metric_name):
    """Apply dollars or percentages when the selected metric needs them."""
    if metric_name in [
        "net_improvement",
        "total_monthly_rent",
        "total_development_cost",
    ]:
        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _: f"${value:,.0f}")
        )
    elif metric_name == "leasable_coverage":
        axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))


def rent_curve_figure(rent_inputs):
    """Show exactly how yard size becomes monthly rent per acre."""
    small_size = rent_inputs["small_yard_breakpoint_acres"]
    small_rent = rent_inputs["small_yard_rent_per_acre"]
    large_size = rent_inputs["large_yard_breakpoint_acres"]
    large_rent = rent_inputs["large_yard_rent_per_acre"]
    scale_function = rent_inputs["scale_function"]

    display_max_acres = max(large_size * 1.20, large_size + 0.25)
    yard_sizes = np.linspace(0.0, display_max_acres, 400)
    assigned_rents = [rent_per_acre(size, rent_inputs, scale_function=scale_function) for size in yard_sizes]

    figure, axis = plt.subplots(figsize=(10, 4.5))

    axis.axvspan(
        0,
        small_size,
        color="#2E8B57",
        alpha=0.10,
        label="Small-yard fixed rate",
    )
    axis.axvspan(
        small_size,
        large_size,
        color="#3366CC",
        alpha=0.08,
        label="Quadratically scaled rate",
    )
    axis.axvspan(
        large_size,
        display_max_acres,
        color="#E67E22",
        alpha=0.10,
        label="Large-yard fixed rate",
    )

    axis.plot(
        yard_sizes,
        assigned_rents,
        color="#244A73",
        linewidth=3,
        label="Assigned rent per acre",
    )

    axis.scatter(
        [small_size, large_size],
        [small_rent, large_rent],
        color=["#2E8B57", "#E67E22"],
        edgecolor="white",
        linewidth=1.5,
        s=90,
        zorder=5,
    )

    axis.axvline(small_size, color="#2E8B57", linestyle="--", alpha=0.7)
    axis.axvline(large_size, color="#E67E22", linestyle="--", alpha=0.7)

    axis.annotate(
        f"Small-yard breakpoint\n{small_size:.3f} acres · ${small_rent:,.0f}/acre",
        xy=(small_size, small_rent),
        xytext=(15, 18),
        textcoords="offset points",
        fontsize=9,
    )
    axis.annotate(
        f"Large-yard breakpoint\n{large_size:.3f} acres · ${large_rent:,.0f}/acre",
        xy=(large_size, large_rent),
        xytext=(-15, -42),
        textcoords="offset points",
        horizontalalignment="right",
        fontsize=9,
    )

    axis.set_title("How Monthly Rent per Acre Is Assigned")
    axis.set_xlabel("Individual yard size (acres)")
    axis.set_ylabel("Monthly rent per acre")
    axis.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"${value:,.0f}")
    )
    axis.grid(alpha=0.2)
    axis.legend(frameon=False, loc="best")
    figure.tight_layout()

    return figure

import plotly.express as px


def scenario_scatter_figure(results, metric_name):
    """Create an interactive scenario scatterplot."""

    plot_data = results

    if len(plot_data) > 12_000:
        plot_data = plot_data.sample(
            12_000,
            random_state=42,
        )

    metric_label = METRIC_LABELS[metric_name]

    figure = px.scatter(
        plot_data,
        x="inner_yard_area_acres",
        y=metric_name,
        color="fill_type",
        size="outer_yard_count",
        size_max=18,
        opacity=0.45,
        render_mode="webgl",
        color_discrete_map=FILL_COLORS,
        category_orders={
            "fill_type": ["full", "line", "cross"],
        },
        labels={
            "inner_yard_area_acres": (
                "Actual inner-yard size (acres)"
            ),
            metric_name: metric_label,
            "fill_type": "Fill type",
            "outer_yard_count": "Outer yards",
            "outer_depth_ft": "Outer depth (ft)",
            "target_inner_yard_size_sf": (
                "Target inner-yard size (sf)"
            ),
        },
        hover_data={
            "inner_yard_area_acres": ":.3f",
            metric_name: ":,.0f",
            "outer_yard_count": True,
            "outer_depth_ft": ":,.0f",
            "target_inner_yard_size_sf": ":,.0f",
        },
        title=f"{metric_label} vs. Inner-Yard Area",
    )

    figure.update_layout(
        height=800,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black"),
        title_font=dict(color="black"),
        legend=dict(
            title=dict(
                text="Fill type",
                font=dict(color="black"),
            ),
            font=dict(color="black"),
            bgcolor="rgba(255, 255, 255, 0.90)",
            bordercolor="#D9D9D9",
            borderwidth=1,
        ),
        hovermode="closest",
    )

    # Plotly uses the raw fill-type values as legend labels.
    # Capitalize them so the legend reads Full, Line, and Cross.
    for trace in figure.data:
        trace.name = trace.name.title()

    figure.update_traces(
        marker=dict(
            line=dict(
                color="black",
                width=0.8,
            )
        )
    )

    figure.update_xaxes(
        gridcolor="#D9D9D9",
        zerolinecolor="#A0A0A0",
        title_font=dict(color="black"),
        tickfont=dict(color="black"),
    )

    figure.update_yaxes(
        gridcolor="#D9D9D9",
        zerolinecolor="#A0A0A0",
        title_font=dict(color="black"),
        tickfont=dict(color="black"),
    )

    if metric_name in [
        "net_improvement",
        "total_monthly_rent",
        "total_development_cost",
    ]:
        figure.update_yaxes(
            tickprefix="$",
            tickformat=",",
        )

    elif metric_name == "leasable_coverage":
        figure.update_yaxes(
            tickformat=".1%",
        )

    return figure


def outer_depth_figure(results, metric_name, inner_size_sf, outer_yard_count):
    """Compare fill types while outer-yard depth changes."""
    selected_rows = results[
        (results["target_inner_yard_size_sf"] == inner_size_sf)
        & (results["outer_yard_count"] == outer_yard_count)
    ]

    figure, axis = plt.subplots(figsize=(10, 5))

    for fill_type in ["full", "line", "cross"]:
        fill_rows = selected_rows[selected_rows["fill_type"] == fill_type]
        if fill_rows.empty:
            continue

        fill_rows = fill_rows.sort_values("outer_depth_ft")
        axis.plot(
            fill_rows["outer_depth_ft"],
            fill_rows[metric_name],
            marker="o",
            markersize=4,
            linewidth=2,
            color=FILL_COLORS[fill_type],
            label=fill_type.title(),
        )

    metric_label = METRIC_LABELS[metric_name]
    axis.set_title(
        f"{metric_label} vs. Outer-Yard Depth\n"
        f"{inner_size_sf:,.0f} sf target inner yard · {outer_yard_count} outer yards"
    )
    axis.set_xlabel("Outer-yard depth (ft)")
    axis.set_ylabel(metric_label)
    format_metric_axis(axis, metric_name)
    axis.grid(alpha=0.2)
    axis.legend(title="Fill type", frameon=False)
    figure.tight_layout()

    return figure


def scenario_heatmap_figure(results, metric_name, fill_type, inner_size_sf):
    """Show the effect of outer depth and outer-yard count together."""
    selected_rows = results[
        (results["fill_type"] == fill_type)
        & (results["target_inner_yard_size_sf"] == inner_size_sf)
    ]

    pivot = selected_rows.pivot_table(
        index="outer_yard_count",
        columns="outer_depth_ft",
        values=metric_name,
        aggfunc="mean",
    )

    figure, axis = plt.subplots(figsize=(11, 5.5))
    image = axis.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis")

    x_step = max(1, len(pivot.columns) // 12)
    x_positions = np.arange(len(pivot.columns))[::x_step]
    x_labels = pivot.columns[::x_step]

    y_step = max(1, len(pivot.index) // 12)
    y_positions = np.arange(len(pivot.index))[::y_step]
    y_labels = pivot.index[::y_step]

    axis.set_xticks(x_positions, x_labels, rotation=45)
    axis.set_yticks(y_positions, y_labels)
    axis.set_xlabel("Outer-yard depth (ft)")
    axis.set_ylabel("Number of outer yards")
    axis.set_title(
        f"{METRIC_LABELS[metric_name]} Heatmap\n"
        f"{fill_type.title()} fill · {inner_size_sf:,.0f} sf target inner yard"
    )

    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label(METRIC_LABELS[metric_name])
    if metric_name in [
        "net_improvement",
        "total_monthly_rent",
        "total_development_cost",
    ]:
        colorbar.formatter = FuncFormatter(lambda value, _: f"${value:,.0f}")
        colorbar.update_ticks()
    elif metric_name == "leasable_coverage":
        colorbar.formatter = PercentFormatter(xmax=1.0)
        colorbar.update_ticks()

    figure.tight_layout()
    return figure
