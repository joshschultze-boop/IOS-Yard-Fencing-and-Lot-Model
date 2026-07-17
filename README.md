# IOS-Yard-Fencing-and-Lot-Model
This repository holds the py files for a fencing application for Industrial Outdoor Storage (IOS) lot divisions. The model uses basic fill types to fill out an approximately rectangular lot with rectangular yards. Note that the code has been written using AI - assistance (Codex, Copilot).

This code was created using a basic model that was hard-coded by Joshua Schultze in a Jupyter notebook.


## Run the application

From this folder:

```powershell
python -m pip install -r requirements.txt
streamlit run homepage.py
```

## Review the code in this order

1. `app_config.py` — default values and plain-English validation rules.
2. `yard_model.py` — geometry, rent, cost, and valuation formulas.
3. `scenario_analysis.py` — the four nested scenario inputs.
4. `app_charts.py` — rent and scenario charts.
5. `site_layout_chart.py` — the mapped rectangular layout drawing.
6. `homepage.py` — input widgets only.
7. `pages/investigative_plots.py` — scenario-page presentation only.
8. `pages/site_layout.py` — layout-page presentation only.

The page files do not contain model formulas.  They collect inputs, call named
functions, and display returned values.

## Where inputs are stored

Clicking **Save inputs** places one nested dictionary at:

```python
st.session_state.model_inputs
```

The two other pages read that dictionary.  If a page is opened before inputs
are saved, it uses the documented values in `app_config.py` and shows a warning.

## Main formulas to validate manually

### Rent curve - This will likely be changed to be more dynamic in updates, but I'm too lazy to update the read me so just check it yourself ;)

At or below the small-yard breakpoint, the small-yard rent is used.  At or
above the large-yard breakpoint, the large-yard rent is used.  Between them:

```text
position = (yard acres - small breakpoint) / (large breakpoint - small breakpoint)
rent = large rent + (small rent - large rent) × (1 - position²)
```

This corrects the discontinuity in the notebook formula.  It is also the exact
function used to draw the rent graph on the homepage.

### Monthly rent

```text
monthly rent = yard acres × assigned monthly rent per acre
```

An additional yard with a positive rent override uses the override instead of
the rent curve.

### Capitalized value and net improvement

```text
annual rent = total monthly rent × 12
capitalized value = annual rent / cap rate
development cost = (fence cost + gate cost) × (1 + effective contingency)
net improvement = capitalized value - development cost
```

### Effective contingency

```text
slanted-side allowance = 2 × (slanted side - lot height) / rectangular perimeter
effective contingency = base contingency + slanted-side allowance
```

Entering zero for the slanted side makes the allowance zero.

### Additional off-map yards

Included additional yards add all of the following:

- their acreage to total site and leasable acreage;
- their rent to monthly rent;
- perimeter fencing after gate openings are removed;
- their gate count to gate cost.

They are listed on the layout page but are not drawn on the rectangular map.

## Automated checks

Run:

```powershell
python -m unittest discover -s tests -v
```

The tests verify the rent breakpoints, decreasing rent curve, notebook geometry
for all three fill types, slanted-side formula, additional-yard inclusion, net
improvement identity, and a small scenario grid.
