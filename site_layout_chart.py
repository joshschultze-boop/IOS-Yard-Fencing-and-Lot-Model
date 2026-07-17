"""Draw the mapped rectangular yard layout with Matplotlib."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Rectangle

from yard_model import calculate_inner_yards


OUTER_COLOR = "#2F6B9A"
INNER_COLOR = "#2E8B57"
FIRE_LANE_COLOR = "#D97724"


def draw_rectangle(
    axis,
    x,
    y,
    width,
    height,
    color,
    alpha=0.30,
    hatch=None,
    line_width=1.0,
    layer=1,
):
    """Add one rectangle to the layout."""
    rectangle = Rectangle(
        (x, y),
        width,
        height,
        facecolor=color,
        edgecolor="black",
        alpha=alpha,
        hatch=hatch,
        linewidth=line_width,
        zorder=layer,
    )
    axis.add_patch(rectangle)


def draw_centered_label(axis, x, y, width, height, text, font_size=7):
    """Place text in the center of a rectangle."""
    axis.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=font_size,
        zorder=10,
    )


def outer_segment_rectangle(edge, offset_ft, length_ft, site_inputs, layout_inputs):
    """Translate a perimeter distance into a physical rectangle."""
    lot_width = site_inputs["lot_width_ft"]
    lot_height = site_inputs["lot_height_ft"]
    outer_depth = layout_inputs["outer_yard_depth_ft"]

    if edge == "top":
        return offset_ft, lot_height - outer_depth, length_ft, outer_depth

    if edge == "right":
        return (
            lot_width - outer_depth,
            lot_height - outer_depth - offset_ft - length_ft,
            outer_depth,
            length_ft,
        )

    if edge == "bottom":
        return lot_width - offset_ft - length_ft, 0, length_ft, outer_depth

    if edge == "left":
        return 0, outer_depth + offset_ft, outer_depth, length_ft

    raise ValueError(f"Unknown lot edge: {edge}")


def draw_outer_yards(axis, site_inputs, layout_inputs):
    """Split the perimeter band evenly into the selected outer-yard count."""
    lot_width = site_inputs["lot_width_ft"]
    lot_height = site_inputs["lot_height_ft"]
    entry_distance = site_inputs["entry_distance_from_ne_corner_ft"]
    outer_depth = layout_inputs["outer_yard_depth_ft"]
    fire_lane = layout_inputs["fire_lane_width_ft"]
    yard_count = layout_inputs["outer_yard_count"]

    entry_center_x = lot_width - entry_distance
    minimum_entry_x = outer_depth
    maximum_entry_x = lot_width - outer_depth - fire_lane
    entry_x = np.clip(
        entry_center_x - fire_lane / 2,
        minimum_entry_x,
        maximum_entry_x,
    )

    perimeter_runs = [
        {"edge": "top", "offset": 0, "length": entry_x},
        {
            "edge": "top",
            "offset": entry_x + fire_lane,
            "length": lot_width - entry_x - fire_lane,
        },
        {
            "edge": "right",
            "offset": 0,
            "length": lot_height - 2 * outer_depth,
        },
        {"edge": "bottom", "offset": 0, "length": lot_width},
        {
            "edge": "left",
            "offset": 0,
            "length": lot_height - 2 * outer_depth,
        },
    ]

    total_run_length = sum(run["length"] for run in perimeter_runs)
    length_per_yard = total_run_length / yard_count

    fragments = []
    run_start = 0.0

    for run in perimeter_runs:
        run_end = run_start + run["length"]

        for yard_index in range(yard_count):
            yard_start = yard_index * length_per_yard
            yard_end = (yard_index + 1) * length_per_yard

            overlap_start = max(yard_start, run_start)
            overlap_end = min(yard_end, run_end)
            overlap_length = overlap_end - overlap_start

            if overlap_length <= 0:
                continue

            local_offset = run["offset"] + overlap_start - run_start
            x, y, width, height = outer_segment_rectangle(
                run["edge"],
                local_offset,
                overlap_length,
                site_inputs,
                layout_inputs,
            )

            alpha = 0.22 if yard_index % 2 == 0 else 0.34
            draw_rectangle(
                axis,
                x,
                y,
                width,
                height,
                OUTER_COLOR,
                alpha=alpha,
                hatch="//",
                line_width=1.1,
            )

            fragments.append(
                {
                    "yard_number": yard_index + 1,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "length": overlap_length,
                }
            )

        run_start = run_end

    # A yard may wrap around a corner.  Label only its longest fragment.
    for yard_number in range(1, yard_count + 1):
        yard_fragments = [
            item for item in fragments if item["yard_number"] == yard_number
        ]
        if not yard_fragments:
            continue

        label_fragment = max(yard_fragments, key=lambda item: item["length"])
        draw_centered_label(
            axis,
            label_fragment["x"],
            label_fragment["y"],
            label_fragment["width"],
            label_fragment["height"],
            f"Outer {yard_number}",
        )

    draw_rectangle(
        axis,
        entry_x,
        lot_height - outer_depth,
        fire_lane,
        outer_depth,
        FIRE_LANE_COLOR,
        alpha=0.50,
        hatch="xx",
        layer=5,
    )
    draw_centered_label(
        axis,
        entry_x,
        lot_height - outer_depth,
        fire_lane,
        outer_depth,
        "Entry",
    )


def draw_perimeter_fire_lane(axis, site_inputs, layout_inputs):
    """Draw the fire-lane ring immediately inside the outer yards."""
    lot_width = site_inputs["lot_width_ft"]
    lot_height = site_inputs["lot_height_ft"]
    outer_depth = layout_inputs["outer_yard_depth_ft"]
    fire_lane = layout_inputs["fire_lane_width_ft"]

    ring_x = outer_depth
    ring_y = outer_depth
    ring_width = lot_width - 2 * outer_depth
    ring_height = lot_height - 2 * outer_depth

    fire_lane_rectangles = [
        (ring_x, ring_y, fire_lane, ring_height),
        (ring_x + ring_width - fire_lane, ring_y, fire_lane, ring_height),
        (ring_x + fire_lane, ring_y, ring_width - 2 * fire_lane, fire_lane),
        (
            ring_x + fire_lane,
            ring_y + ring_height - fire_lane,
            ring_width - 2 * fire_lane,
            fire_lane,
        ),
    ]

    for x, y, width, height in fire_lane_rectangles:
        draw_rectangle(
            axis,
            x,
            y,
            width,
            height,
            FIRE_LANE_COLOR,
            alpha=0.40,
            hatch="xx",
            layer=2,
        )


def draw_inner_yards(axis, inner_calculation):
    """Draw every calculated inner-yard cell and number it."""
    next_yard_number = 1

    for section in inner_calculation["sections"]:
        grid = section["grid"]
        rows = grid["rows"]

        if grid["split_axis"] == "x":
            cell_width = section["width"] / 2
            cell_height = section["height"] / rows

            cells = []
            for column in range(2):
                for row in range(rows):
                    cells.append(
                        (
                            section["x"] + column * cell_width,
                            section["y"] + row * cell_height,
                            cell_width,
                            cell_height,
                        )
                    )
        else:
            cell_width = section["width"] / rows
            cell_height = section["height"] / 2

            cells = []
            for band in range(2):
                for column in range(rows):
                    cells.append(
                        (
                            section["x"] + column * cell_width,
                            section["y"] + band * cell_height,
                            cell_width,
                            cell_height,
                        )
                    )

        for x, y, width, height in cells:
            draw_rectangle(
                axis,
                x,
                y,
                width,
                height,
                INNER_COLOR,
                alpha=0.35,
                line_width=0.75,
                layer=3,
            )

            if inner_calculation["yard_count"] <= 80:
                draw_centered_label(
                    axis,
                    x,
                    y,
                    width,
                    height,
                    str(next_yard_number),
                )

            next_yard_number += 1


def site_layout_figure(inputs, fill_type=None):
    """Return the complete site-layout figure and its inner-yard calculation."""
    site = inputs["site"]
    layout = dict(inputs["layout"])
    if fill_type:
        layout["fill_type"] = fill_type

    inner = calculate_inner_yards(site, layout)
    figure, axis = plt.subplots(figsize=(11, 8))

    draw_rectangle(
        axis,
        0,
        0,
        site["lot_width_ft"],
        site["lot_height_ft"],
        color="none",
        alpha=1.0,
        line_width=2.0,
        layer=20,
    )
    draw_outer_yards(axis, site, layout)
    draw_perimeter_fire_lane(axis, site, layout)

    for lane in inner["center_fire_lanes"]:
        draw_rectangle(
            axis,
            lane["x"],
            lane["y"],
            lane["width"],
            lane["height"],
            FIRE_LANE_COLOR,
            alpha=0.40,
            hatch="xx",
            layer=2,
        )

    draw_inner_yards(axis, inner)

    average_area_sf = inner["average_yard_area_sf"]
    average_area_acres = inner["average_yard_area_acres"]
    axis.set_title(
        f"{layout['fill_type'].title()} Fill Layout\n"
        f"{inner['yard_count']} inner yards · "
        f"{average_area_sf:,.0f} sf ({average_area_acres:.3f} acres) average"
    )
    axis.set_xlabel("Feet")
    axis.set_ylabel("Feet")
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlim(-25, site["lot_width_ft"] + 25)
    axis.set_ylim(-25, site["lot_height_ft"] + 25)
    axis.grid(alpha=0.20)

    legend_items = [
        Patch(
            facecolor=OUTER_COLOR,
            edgecolor="black",
            alpha=0.25,
            hatch="//",
            label="Outer yards",
        ),
        Patch(
            facecolor=INNER_COLOR,
            edgecolor="black",
            alpha=0.35,
            label="Inner yards",
        ),
        Patch(
            facecolor=FIRE_LANE_COLOR,
            edgecolor="black",
            alpha=0.40,
            hatch="xx",
            label="Fire lane / access",
        ),
    ]
    axis.legend(handles=legend_items, loc="upper right")
    figure.tight_layout()

    return figure, inner
