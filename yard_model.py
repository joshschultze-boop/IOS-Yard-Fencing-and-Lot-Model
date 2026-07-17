"""Core geometry and financial calculations for the yard model.

Every function in this file receives its inputs as arguments and returns data.
There is no Streamlit code and there are no notebook-style global variables.
That makes each formula easy to review and test on its own.
"""

import math

from app_config import ACRE_TO_SQFT, effective_contingency_rate


def acres_to_square_feet(acres):
    """Convert acres to square feet."""
    return acres * ACRE_TO_SQFT


def square_feet_to_acres(square_feet):
    """Convert square feet to acres."""
    return square_feet / ACRE_TO_SQFT


def rent_per_acre(yard_size_acres, rent_inputs, scale_function=None):
    """Assign monthly rent per acre from the two size breakpoints.

    The price is fixed outside the breakpoints.  Between them, the price
    declines along a quadratic curve.  This version is continuous: it equals
    the small-yard price at the first breakpoint and the large-yard price at
    the second breakpoint.
    """
    small_size = rent_inputs["small_yard_breakpoint_acres"]
    small_rent = rent_inputs["small_yard_rent_per_acre"]
    large_size = rent_inputs["large_yard_breakpoint_acres"]
    large_rent = rent_inputs["large_yard_rent_per_acre"]
    if scale_function is None:
        scale_function = rent_inputs.get("scale_function", "Linear")

    if yard_size_acres <= small_size:
        return small_rent

    if yard_size_acres >= large_size:
        return large_rent

    size_position = (yard_size_acres - small_size) / (large_size - small_size)
    rent_difference = small_rent - large_rent

    if scale_function == "Linear":
        return large_rent + rent_difference * (1 - size_position)
    elif scale_function == "Quadratic":
        return large_rent + rent_difference * (1 - size_position**2)
    elif scale_function == "Exponential":
        return large_rent + (rent_difference * (1 - math.exp(size_position - 1))) / (1-math.exp(-1))
    elif scale_function == "Logistic":
        steepness = 8.0
        midpoint = 0.5

        # Decreasing logistic function.
        raw_value = 1 / (
             1 + math.exp(
                steepness * (size_position - midpoint)
            )
        )

        # Calculate its values at the two breakpoints.
        raw_at_small_breakpoint = 1 / (
             1 + math.exp(
                steepness * (0 - midpoint)
             )
         )

        raw_at_large_breakpoint = 1 / (
            1 + math.exp(
                steepness * (1 - midpoint)
            )
        )

        # Normalize the result so it is exactly 1 at the small
        # breakpoint and exactly 0 at the large breakpoint.
        premium_fraction = (
            raw_value - raw_at_large_breakpoint
        ) / (
            raw_at_small_breakpoint
            - raw_at_large_breakpoint
        )

        return large_rent + rent_difference * premium_fraction
    else:
        raise ValueError(f"Unknown scale function: {scale_function}")


def calculate_inner_grid(
    rectangle_width_ft,
    rectangle_height_ft,
    target_yard_size_sf,
    minimum_depth_ft,
    minimum_frontage_ft,
    depth_uses_long_side,
):
    """Divide one rectangular section into two columns or two horizontal bands.

    ``depth_uses_long_side`` preserves the notebook's orientation rules:

    * line and cross fill use the longer side as the calculation width;
    * full fill uses the shorter side as the calculation width.

    The calculation width is divided by two to create two opposing yards.
    The calculation height is divided into rows.
    """
    if rectangle_width_ft <= 0 or rectangle_height_ft <= 0:
        raise ValueError("The inner rectangle has no usable area.")

    longer_side = max(rectangle_width_ft, rectangle_height_ft)
    shorter_side = min(rectangle_width_ft, rectangle_height_ft)

    if depth_uses_long_side:
        calculation_width = longer_side
        calculation_height = shorter_side
    else:
        calculation_width = shorter_side
        calculation_height = longer_side

    if calculation_width == rectangle_width_ft:
        split_axis = "x"
    else:
        split_axis = "y"

    rectangle_area_sf = calculation_width * calculation_height

    if rectangle_area_sf < target_yard_size_sf * 2:
        raise ValueError("The inner rectangle is too small for two target-size yards.")

    initial_yard_count = math.ceil(
        (rectangle_area_sf / 2) / target_yard_size_sf
    ) * 2

    yard_depth_ft = calculation_width / 2
    initial_frontage_ft = calculation_height / (initial_yard_count / 2)

    if yard_depth_ft < minimum_depth_ft:
        raise ValueError("Inner-yard depth is below the selected minimum.")

    # If the target size creates yards that are too narrow, use the minimum
    # frontage and reduce the number of rows.
    working_frontage_ft = max(initial_frontage_ft, minimum_frontage_ft)
    rows = math.floor(
        (rectangle_area_sf / 2) / (yard_depth_ft * working_frontage_ft)
    )
    rows = max(1, rows)

    yard_count = rows * 2
    final_frontage_ft = calculation_height / rows

    if final_frontage_ft < minimum_frontage_ft:
        raise ValueError("Inner-yard frontage is below the selected minimum.")

    yard_area_sf = yard_depth_ft * final_frontage_ft

    # This is the same fence formula used by inner_section_fill() in the
    # notebook: three long edges, two end edges, and the row dividers.
    fence_length_ft = (
        calculation_height * 3
        + calculation_width * 2
        + (rows - 1) * calculation_width
    )

    return {
        "yard_count": yard_count,
        "rows": rows,
        "split_axis": split_axis,
        "yard_depth_ft": yard_depth_ft,
        "yard_frontage_ft": final_frontage_ft,
        "yard_area_sf": yard_area_sf,
        "yard_area_acres": square_feet_to_acres(yard_area_sf),
        "fence_length_ft": fence_length_ft,
    }


def build_inner_sections(site_inputs, layout_inputs, fill_type=None):
    """Describe the physical rectangles available for inner yards."""
    selected_fill = fill_type or layout_inputs["fill_type"]

    lot_width = site_inputs["lot_width_ft"]
    lot_height = site_inputs["lot_height_ft"]
    outer_depth = layout_inputs["outer_yard_depth_ft"]
    fire_lane = layout_inputs["fire_lane_width_ft"]

    usable_x = outer_depth + fire_lane
    usable_y = outer_depth + fire_lane
    usable_width = lot_width - 2 * outer_depth - 2 * fire_lane
    usable_height = lot_height - 2 * outer_depth - 2 * fire_lane

    if usable_width <= 0 or usable_height <= 0:
        raise ValueError("Outer yards and fire lanes leave no inner-yard area.")

    sections = []
    center_fire_lanes = []

    if selected_fill == "full":
        sections.append(
            {
                "x": usable_x,
                "y": usable_y,
                "width": usable_width,
                "height": usable_height,
                "depth_uses_long_side": False,
            }
        )

    elif selected_fill == "line":
        side_width = usable_width / 2 - fire_lane / 2
        center_x = usable_x + side_width

        if side_width <= 0:
            raise ValueError("Line fill leaves no room beside its center fire lane.")

        sections.extend(
            [
                {
                    "x": usable_x,
                    "y": usable_y,
                    "width": side_width,
                    "height": usable_height,
                    "depth_uses_long_side": True,
                },
                {
                    "x": center_x + fire_lane,
                    "y": usable_y,
                    "width": side_width,
                    "height": usable_height,
                    "depth_uses_long_side": True,
                },
            ]
        )
        center_fire_lanes.append(
            {
                "x": center_x,
                "y": usable_y,
                "width": fire_lane,
                "height": usable_height,
            }
        )

    elif selected_fill == "cross":
        section_width = usable_width / 2 - fire_lane / 2
        section_height = usable_height / 2 - fire_lane / 2
        center_x = usable_x + section_width
        center_y = usable_y + section_height

        if section_width <= 0 or section_height <= 0:
            raise ValueError("Cross fill leaves no room around its center fire lanes.")

        for x in [usable_x, center_x + fire_lane]:
            for y in [usable_y, center_y + fire_lane]:
                sections.append(
                    {
                        "x": x,
                        "y": y,
                        "width": section_width,
                        "height": section_height,
                        "depth_uses_long_side": True,
                    }
                )

        center_fire_lanes.extend(
            [
                {
                    "x": center_x,
                    "y": usable_y,
                    "width": fire_lane,
                    "height": usable_height,
                },
                {
                    "x": usable_x,
                    "y": center_y,
                    "width": usable_width,
                    "height": fire_lane,
                },
            ]
        )

    else:
        raise ValueError("Fill type must be full, line, or cross.")

    return {
        "sections": sections,
        "center_fire_lanes": center_fire_lanes,
        "usable_width_ft": usable_width,
        "usable_height_ft": usable_height,
    }


def calculate_inner_yards(site_inputs, layout_inputs, fill_type=None):
    """Calculate yard count, average area, and fencing for all inner sections."""
    section_plan = build_inner_sections(site_inputs, layout_inputs, fill_type)

    total_yard_count = 0
    total_yard_area_sf = 0.0
    total_fence_length_ft = 0.0
    calculated_sections = []

    for section in section_plan["sections"]:
        grid = calculate_inner_grid(
            rectangle_width_ft=section["width"],
            rectangle_height_ft=section["height"],
            target_yard_size_sf=layout_inputs["target_inner_yard_size_sf"],
            minimum_depth_ft=layout_inputs["minimum_inner_yard_depth_ft"],
            minimum_frontage_ft=layout_inputs["minimum_inner_yard_frontage_ft"],
            depth_uses_long_side=section["depth_uses_long_side"],
        )

        calculated_section = dict(section)
        calculated_section["grid"] = grid
        calculated_sections.append(calculated_section)

        total_yard_count += grid["yard_count"]
        total_yard_area_sf += grid["yard_count"] * grid["yard_area_sf"]
        total_fence_length_ft += grid["fence_length_ft"]

    average_yard_area_sf = total_yard_area_sf / total_yard_count

    return {
        "yard_count": total_yard_count,
        "average_yard_area_sf": average_yard_area_sf,
        "average_yard_area_acres": square_feet_to_acres(average_yard_area_sf),
        "total_yard_area_acres": square_feet_to_acres(total_yard_area_sf),
        "gross_fence_length_ft": total_fence_length_ft,
        "sections": calculated_sections,
        "center_fire_lanes": section_plan["center_fire_lanes"],
        "usable_width_ft": section_plan["usable_width_ft"],
        "usable_height_ft": section_plan["usable_height_ft"],
    }


def calculate_outer_yards(site_inputs, layout_inputs):
    """Calculate the perimeter-band yards using the notebook formulas."""
    lot_width = site_inputs["lot_width_ft"]
    lot_height = site_inputs["lot_height_ft"]
    outer_depth = layout_inputs["outer_yard_depth_ft"]
    fire_lane = layout_inputs["fire_lane_width_ft"]
    yard_count = layout_inputs["outer_yard_count"]

    total_area_sf = (
        lot_width * outer_depth
        - outer_depth * fire_lane
        + lot_width * outer_depth
        + 2 * (lot_height - 2 * outer_depth) * outer_depth
    )

    if total_area_sf <= 0:
        raise ValueError("The outer-yard inputs produce a non-positive area.")

    outside_perimeter = 2 * lot_width + 2 * lot_height - fire_lane
    short_end_fences = 2 * outer_depth
    top_inner_fence = lot_width - 2 * outer_depth - fire_lane
    bottom_inner_fence = lot_width - 2 * outer_depth
    side_inner_fences = 2 * (lot_height - 2 * outer_depth)
    yard_dividers = outer_depth * (yard_count - 1)

    gross_fence_length_ft = (
        outside_perimeter
        + short_end_fences
        + top_inner_fence
        + bottom_inner_fence
        + side_inner_fences
        + yard_dividers
    )

    total_area_acres = square_feet_to_acres(total_area_sf)

    return {
        "yard_count": yard_count,
        "yard_area_acres": total_area_acres / yard_count,
        "total_yard_area_acres": total_area_acres,
        "gross_fence_length_ft": gross_fence_length_ft,
    }


def calculate_irregular_yards(inputs):
    """Calculate the off-map yards entered on the homepage."""
    rent_inputs = inputs["rent"]
    costs = inputs["costs"]

    included_yards = []
    total_area_acres = 0.0
    total_monthly_rent = 0.0
    total_net_fence_ft = 0.0
    total_gate_count = 0

    for yard in inputs["irregular_yards"]:
        if not yard["include_in_financials"]:
            continue

        yard_rent = yard["rent_per_acre_override"]
        if yard_rent <= 0:
            yard_rent = rent_per_acre(yard["area_acres"], rent_inputs)

        gate_opening_ft = yard["gate_count"] * yard["gate_length_ft"]
        net_fence_ft = yard["perimeter_ft"] - gate_opening_ft
        monthly_rent = yard["area_acres"] * yard_rent

        included_yards.append(
            {
                "yard_name": yard["yard_name"],
                "area_acres": yard["area_acres"],
                "rent_per_acre": yard_rent,
                "monthly_rent": monthly_rent,
                "net_fence_length_ft": net_fence_ft,
                "gate_count": yard["gate_count"],
            }
        )

        total_area_acres += yard["area_acres"]
        total_monthly_rent += monthly_rent
        total_net_fence_ft += net_fence_ft
        total_gate_count += yard["gate_count"]

    return {
        "yard_count": len(included_yards),
        "total_area_acres": total_area_acres,
        "monthly_rent": total_monthly_rent,
        "fencing_cost": total_net_fence_ft * costs["fence_cost_per_ft"],
        "gate_cost": total_gate_count * costs["gate_cost_each"],
        "yards": included_yards,
    }


def calculate_model(inputs, layout_overrides=None):
    """Run one complete geometry and financial scenario.

    ``layout_overrides`` lets the scenario page change the fill type, target
    inner-yard size, outer depth, or outer-yard count without changing the
    saved homepage inputs.
    """
    layout = dict(inputs["layout"])
    if layout_overrides:
        layout.update(layout_overrides)

    costs = inputs["costs"]
    rent_inputs = inputs["rent"]

    outer = calculate_outer_yards(inputs["site"], layout)
    inner = calculate_inner_yards(inputs["site"], layout)
    irregular = calculate_irregular_yards(inputs)

    outer_rent_per_acre = rent_per_acre(outer["yard_area_acres"], rent_inputs)
    inner_rent_per_acre = rent_per_acre(
        inner["average_yard_area_acres"], rent_inputs
    )

    outer_monthly_rent = (
        outer["total_yard_area_acres"] * outer_rent_per_acre
    )
    inner_monthly_rent = (
        inner["total_yard_area_acres"] * inner_rent_per_acre
    )
    mapped_monthly_rent = outer_monthly_rent + inner_monthly_rent
    total_monthly_rent = mapped_monthly_rent + irregular["monthly_rent"]

    mapped_gate_count = outer["yard_count"] + inner["yard_count"]
    mapped_gate_opening_ft = (
        outer["yard_count"] * costs["outer_gate_length_ft"]
        + inner["yard_count"] * costs["inner_gate_length_ft"]
    )
    mapped_gross_fence_ft = (
        outer["gross_fence_length_ft"] + inner["gross_fence_length_ft"]
    )
    mapped_net_fence_ft = mapped_gross_fence_ft - mapped_gate_opening_ft

    if mapped_net_fence_ft < 0:
        raise ValueError("Gate openings exceed the mapped fence length.")

    mapped_fencing_cost = mapped_net_fence_ft * costs["fence_cost_per_ft"]
    mapped_gate_cost = mapped_gate_count * costs["gate_cost_each"]

    total_fencing_cost = mapped_fencing_cost + irregular["fencing_cost"]
    total_gate_cost = mapped_gate_cost + irregular["gate_cost"]
    cost_before_contingency = total_fencing_cost + total_gate_cost

    contingency_rate = effective_contingency_rate(inputs)
    total_development_cost = cost_before_contingency * (1 + contingency_rate)

    annual_rent = total_monthly_rent * 12
    capitalized_value = annual_rent / costs["cap_rate"]
    net_improvement = capitalized_value - total_development_cost

    mapped_lot_acres = square_feet_to_acres(
        inputs["site"]["lot_width_ft"] * inputs["site"]["lot_height_ft"]
    )
    total_site_acres = mapped_lot_acres + irregular["total_area_acres"]
    total_leasable_acres = (
        outer["total_yard_area_acres"]
        + inner["total_yard_area_acres"]
        + irregular["total_area_acres"]
    )
    leasable_coverage = total_leasable_acres / total_site_acres

    return {
        "fill_type": layout["fill_type"],
        "target_inner_yard_size_sf": layout["target_inner_yard_size_sf"],
        "outer_depth_ft": layout["outer_yard_depth_ft"],
        "outer_yard_count": outer["yard_count"],
        "outer_yard_area_acres": outer["yard_area_acres"],
        "outer_rent_per_acre": outer_rent_per_acre,
        "inner_yard_count": inner["yard_count"],
        "inner_yard_area_acres": inner["average_yard_area_acres"],
        "inner_rent_per_acre": inner_rent_per_acre,
        "additional_yard_count": irregular["yard_count"],
        "mapped_monthly_rent": mapped_monthly_rent,
        "additional_monthly_rent": irregular["monthly_rent"],
        "total_monthly_rent": total_monthly_rent,
        "annual_rent": annual_rent,
        "capitalized_value": capitalized_value,
        "total_fencing_cost": total_fencing_cost,
        "total_gate_cost": total_gate_cost,
        "cost_before_contingency": cost_before_contingency,
        "effective_contingency_rate": contingency_rate,
        "total_development_cost": total_development_cost,
        "net_improvement": net_improvement,
        "mapped_lot_acres": mapped_lot_acres,
        "additional_site_acres": irregular["total_area_acres"],
        "total_site_acres": total_site_acres,
        "total_leasable_acres": total_leasable_acres,
        "leasable_coverage": leasable_coverage,
    }


def yard_summary_rows(inputs, fill_type=None):
    """Build the small yard-type table shown on the layout page."""
    layout = dict(inputs["layout"])
    if fill_type:
        layout["fill_type"] = fill_type

    outer = calculate_outer_yards(inputs["site"], layout)
    inner = calculate_inner_yards(inputs["site"], layout)
    irregular = calculate_irregular_yards(inputs)
    rent_inputs = inputs["rent"]

    rows = [
        {
            "Yard type": "Mapped outer yards",
            "Count": outer["yard_count"],
            "Average acres": outer["yard_area_acres"],
            "Rent / acre / month": rent_per_acre(
                outer["yard_area_acres"], rent_inputs
            ),
        },
        {
            "Yard type": "Mapped inner yards",
            "Count": inner["yard_count"],
            "Average acres": inner["average_yard_area_acres"],
            "Rent / acre / month": rent_per_acre(
                inner["average_yard_area_acres"], rent_inputs
            ),
        },
    ]

    for yard in irregular["yards"]:
        rows.append(
            {
                "Yard type": yard["yard_name"] + " (not mapped)",
                "Count": 1,
                "Average acres": yard["area_acres"],
                "Rent / acre / month": yard["rent_per_acre"],
            }
        )

    return rows
