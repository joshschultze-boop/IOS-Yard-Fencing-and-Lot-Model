"""Default inputs and validation rules for the yard model application.

This file contains no Streamlit code and no financial calculations.  Its only
jobs are to define the starting inputs and explain which inputs are invalid.
"""

from copy import deepcopy


ACRE_TO_SQFT = 43_560.0
FILL_TYPES = ["full", "line", "cross"]


# These values come from the input cell in union_pacific_yard_model.ipynb.
DEFAULT_INPUTS = {
    "site": {
        "lot_width_ft": 889.0,
        "lot_height_ft": 710.0,
        "slanted_side_length_ft": 819.0,
        "entry_distance_from_ne_corner_ft": 335.0,
    },
    "layout": {
        "fill_type": "full",
        "target_inner_yard_size_sf": 5_000.0,
        "outer_yard_depth_ft": 200.0,
        "outer_yard_count": 6,
        "fire_lane_width_ft": 40.0,
        "minimum_inner_yard_depth_ft": 57.0,
        "minimum_inner_yard_frontage_ft": 57.0,
    },
    "costs": {
        "fence_cost_per_ft": 45.0,
        "gate_cost_each": 4_500.0,
        "outer_gate_length_ft": 24.0,
        "inner_gate_length_ft": 20.0,
        "base_contingency_rate": 0.20,
        "cap_rate": 0.075,
    },
    "rent": {
        "small_yard_breakpoint_acres": 0.01,
        "small_yard_rent_per_acre": 6_800.0,
        "large_yard_breakpoint_acres": 4.0,
        "large_yard_rent_per_acre": 4_000.0,
    },
    "irregular_yards": [
        {
            "yard_name": "Extra Yard",
            "area_acres": 1,
            "perimeter_ft": 834.84,
            "gate_count": 1,
            "gate_length_ft": 24.0,
            "rent_per_acre_override": 0.0,
            "include_in_financials": True,
            "notes": "Off-map irregular yard.",
        }
    ],
    "scenario_grid": {
        "fill_types": ["full", "line", "cross"],
        "inner_yard_size_min_sf": 5_000,
        "inner_yard_size_max_sf": 11_000,
        "inner_yard_size_step_sf": 250,
        "outer_depth_min_ft": 85,
        "outer_depth_max_ft": 300,
        "outer_depth_step_ft": 25,
        "outer_yard_count_min": 1,
        "outer_yard_count_max": 10,
        "outer_yard_count_step": 1,
    },
}


def copy_default_inputs():
    """Return a copy so callers cannot accidentally change DEFAULT_INPUTS."""
    return deepcopy(DEFAULT_INPUTS)


def slanted_side_adjustment(site_inputs):
    """Calculate the net added perimeter allowance as a decimal rate."""
    lot_width = site_inputs["lot_width_ft"]
    lot_height = site_inputs["lot_height_ft"]
    slanted_side = site_inputs["slanted_side_length_ft"]

    if slanted_side == 0:
        return 0.0

    rectangular_perimeter = 2 * (lot_width + lot_height)
    extra_perimeter = 2 * (slanted_side - lot_height)
    return extra_perimeter / rectangular_perimeter


def effective_contingency_rate(inputs):
    """Add the base contingency and slanted-side allowance."""
    base_rate = inputs["costs"]["base_contingency_rate"]
    return base_rate + slanted_side_adjustment(inputs["site"])


def inclusive_range_count(minimum, maximum, step):
    """Count values in an inclusive range such as 5, 10, 15."""
    if step <= 0 or maximum < minimum:
        return 0
    return ((maximum - minimum) // step) + 1


def scenario_count(inputs):
    """Return the number of cases requested on the scenario page."""
    grid = inputs["scenario_grid"]

    inner_size_count = inclusive_range_count(
        grid["inner_yard_size_min_sf"],
        grid["inner_yard_size_max_sf"],
        grid["inner_yard_size_step_sf"],
    )
    outer_depth_count = inclusive_range_count(
        grid["outer_depth_min_ft"],
        grid["outer_depth_max_ft"],
        grid["outer_depth_step_ft"],
    )
    outer_yard_count = inclusive_range_count(
        grid["outer_yard_count_min"],
        grid["outer_yard_count_max"],
        grid["outer_yard_count_step"],
    )

    return (
        len(grid["fill_types"])
        * inner_size_count
        * outer_depth_count
        * outer_yard_count
    )


def validate_inputs(inputs):
    """Return a list of plain-English validation errors."""
    errors = []
    site = inputs["site"]
    layout = inputs["layout"]
    costs = inputs["costs"]
    rent = inputs["rent"]
    grid = inputs["scenario_grid"]

    if site["lot_width_ft"] <= 0 or site["lot_height_ft"] <= 0:
        errors.append("Lot width and lot height must be greater than zero.")

    if site["entry_distance_from_ne_corner_ft"] > site["lot_width_ft"]:
        errors.append("The entry distance cannot be greater than the lot width.")

    slanted_side = site["slanted_side_length_ft"]
    if slanted_side != 0 and slanted_side < site["lot_height_ft"]:
        errors.append(
            "The slanted side must be at least the lot height, or zero to disable it."
        )

    if layout["fill_type"] not in FILL_TYPES:
        errors.append("The baseline fill type must be full, line, or cross.")

    if layout["target_inner_yard_size_sf"] <= 0:
        errors.append("Target inner-yard size must be greater than zero.")

    if layout["outer_yard_count"] < 1:
        errors.append("At least one outer yard is required.")

    if layout["fire_lane_width_ft"] <= 0:
        errors.append("Fire-lane width must be greater than zero.")

    usable_width = site["lot_width_ft"] - 2 * (
        layout["outer_yard_depth_ft"] + layout["fire_lane_width_ft"]
    )
    usable_height = site["lot_height_ft"] - 2 * (
        layout["outer_yard_depth_ft"] + layout["fire_lane_width_ft"]
    )

    if usable_width <= 0 or usable_height <= 0:
        errors.append(
            "Outer-yard depth and the perimeter fire lane leave no inner-yard area."
        )

    if layout["fill_type"] in ["line", "cross"]:
        if usable_width <= layout["fire_lane_width_ft"]:
            errors.append("The selected fill needs more width for its center fire lane.")
        if layout["fill_type"] == "cross":
            if usable_height <= layout["fire_lane_width_ft"]:
                errors.append(
                    "Cross fill needs more height for its horizontal fire lane."
                )

    if costs["cap_rate"] <= 0:
        errors.append("Cap rate must be greater than zero.")

    if costs["base_contingency_rate"] < 0:
        errors.append("Base contingency cannot be negative.")

    small_size = rent["small_yard_breakpoint_acres"]
    large_size = rent["large_yard_breakpoint_acres"]
    small_rent = rent["small_yard_rent_per_acre"]
    large_rent = rent["large_yard_rent_per_acre"]

    if small_size >= large_size:
        errors.append("The small-yard breakpoint must be below the large-yard breakpoint.")

    if small_rent < large_rent:
        errors.append("Small-yard rent must be at least as high as large-yard rent.")

    for yard in inputs["irregular_yards"]:
        yard_name = yard["yard_name"] or "Unnamed additional yard"
        if not yard["yard_name"].strip():
            errors.append("Every additional yard needs a name.")
        if yard["area_acres"] <= 0:
            errors.append(f"{yard_name} needs an area greater than zero.")
        if yard["perimeter_ft"] <= 0:
            errors.append(f"{yard_name} needs a perimeter greater than zero.")
        if yard["gate_count"] < 0 or yard["gate_length_ft"] < 0:
            errors.append(f"{yard_name} cannot have a negative gate input.")
        gate_openings = yard["gate_count"] * yard["gate_length_ft"]
        if gate_openings > yard["perimeter_ft"]:
            errors.append(f"{yard_name}'s gate openings exceed its perimeter.")

    if not grid["fill_types"]:
        errors.append("Select at least one fill type for scenario analysis.")

    range_checks = [
        (
            "Inner-yard size",
            grid["inner_yard_size_min_sf"],
            grid["inner_yard_size_max_sf"],
            grid["inner_yard_size_step_sf"],
        ),
        (
            "Outer depth",
            grid["outer_depth_min_ft"],
            grid["outer_depth_max_ft"],
            grid["outer_depth_step_ft"],
        ),
        (
            "Outer-yard count",
            grid["outer_yard_count_min"],
            grid["outer_yard_count_max"],
            grid["outer_yard_count_step"],
        ),
    ]

    for label, minimum, maximum, step in range_checks:
        if minimum > maximum:
            errors.append(f"{label} minimum cannot exceed its maximum.")
        if step <= 0:
            errors.append(f"{label} step must be greater than zero.")

    return errors
