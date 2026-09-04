# Local Ballistics Calculator

A local, offline replacement for JBM Ballistics' trajectory calculator:
point-mass (3DoF) drop/velocity/energy tables, and a matplotlib chart
comparing drop-vs-range across multiple loads. Optionally pulls bullet
weight/velocity/BC straight from the `handloads` project's database.

## Where the math comes from

Trajectory physics are computed by [`py_ballisticcalc`][pbc] (LGPL-3), not
hand-derived. It's a direct Python descendant of **JBM Ballistics' own
published C solver**, extended per Bryan Litz's *Applied Ballistics*
methodology, with per-integration-engine CI test suites. This file
(`trajectory.py`) is just a thin adapter between the GUI's plain numbers and
that library's unit-aware API -- see the `RISK NOTICE` in `trajectory.py`'s
docstring, inherited from the library itself: treat results as an aid, not a
substitute for a chronograph, a verified zero, and field judgment.

`trajectory.py`'s own `__main__` block re-derives one of the library's
documented reference examples and matches it exactly, digit-for-digit --
run `python3 trajectory.py` to see that check for yourself.

[pbc]: https://github.com/o-murphy/py-ballisticcalc

## Setup

Needs `python3-tk` (same as the handloads project -- skip if already
installed):

```
sudo apt install -y python3-tk
```

Dependencies (`py_ballisticcalc`, `matplotlib`) are vendored into `./vendor`
rather than a venv (no `python3-venv` available when this was built). To
(re)install them:

```
pip install --target=./vendor -r requirements.txt
```

## Run

```
python3 app.py
```

## Using it

- Fill in the left-hand form: bullet weight, muzzle velocity, ballistic
  coefficient + drag model (G1 or G7 -- use whichever the bullet maker
  publishes), sight height, zero range, and optionally atmosphere/wind/angle.
  Diameter and length are optional and only affect spin drift (windage).
- **Compute** fills in the trajectory table and shows a dotted preview line
  on the chart.
- **Add / Update Curve on Chart** pins the current inputs as a named,
  permanent line on the comparison chart (rename via the "Curve name" field
  before adding to build up a multi-load comparison). Add as many as you
  want; remove one via the list + **Remove Selected**, or **Clear All**.
- The chart's y-axis is drop *relative to line of sight* (what JBM calls
  "Path"/"Drop") -- it accounts for sight height and the barrel angle needed
  to zero at your chosen zero range, not raw drop below the bore.

## Handloads integration

**Load from Handloads...** opens a picker over the `handloads` project's
`handloads.db` (expected as a sibling directory, `../handloads`). Selecting
a load pulls in bullet weight, your chronographed average velocity, and
(if set) ballistic coefficient + drag model + diameter/length.

To get full integration for a load, open it in the handloads app and fill in:
**Ballistic coefficient**, **BC drag model (G1/G7)**, and optionally
**Bullet diameter (in)** / **Bullet length (in)**. These four fields were
added to `handloads.db`'s schema for this project (existing records are
untouched -- the fields are just blank until you fill them in).

If `../handloads` isn't found, the picker button is disabled and everything
else still works with manual entry.

## Known limitations

- No powder-temperature velocity sensitivity modeling (the library supports
  it; this GUI doesn't expose it -- your muzzle velocity is used as-is
  regardless of the temperature field, which only affects air density/drag).
- Twist rate isn't pulled automatically from a linked handloads firearm
  (its `twist_rate` field is a free-text string like `"1:8"`, not a plain
  number) -- enter it by hand in the **Twist rate** field to enable spin
  drift for that calculation; leave it at 0 to disable spin drift (windage
  then reflects wind drift only).
- Like JBM itself, this is a simulation aid -- always verify a load's actual
  zero and drop at the range before relying on it for a shot you can't take back.
