"""Thin wrapper around py_ballisticcalc for the local trajectory calculator GUI.

py_ballisticcalc (LGPL-3, https://github.com/o-murphy/py-ballisticcalc) is a
direct Python descendant of JBM Ballistics' own published point-mass (3DoF)
solver, extended per Bryan Litz's Applied Ballistics methodology. All actual
drag-table physics and integration live there -- this module only adapts our
GUI's plain-number inputs into its unit-aware API and flattens results back
to plain dicts for the Treeview/matplotlib code.

RISK NOTICE (inherited from py_ballisticcalc): this performs an approximate
simulation. Treat results as an aid, not a substitute for a chronograph,
verified zero, and your own judgment in the field.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

from py_ballisticcalc import (  # noqa: E402
    Ammo,
    Atmo,
    Calculator,
    DragModel,
    RangeError,
    Shot,
    TableG1,
    TableG7,
    Unit,
    Weapon,
    Wind,
)

DRAG_TABLES = {"G1": TableG1, "G7": TableG7}


class TrajectoryPoint(TypedDict):
    range_yd: float
    time_s: float
    velocity_fps: float
    mach: float
    drop_in: float          # slant_height: drop relative to line of sight (what JBM calls "Path"/"Drop")
    drop_moa: float
    windage_in: float
    windage_moa: float
    energy_ftlb: float


def compute_trajectory(
    *,
    weight_gr: float,
    muzzle_velocity_fps: float,
    bc: float,
    drag_model: str = "G1",
    diameter_in: float = 0.0,
    length_in: float = 0.0,
    twist_in: float = 0.0,
    sight_height_in: float = 1.5,
    zero_range_yd: float = 100.0,
    look_angle_deg: float = 0.0,
    altitude_ft: float = 0.0,
    pressure_inhg: float | None = None,
    temperature_f: float = 59.0,
    humidity_pct: float = 0.0,
    wind_speed_mph: float = 0.0,
    wind_direction_deg: float = 0.0,
    max_range_yd: float = 500.0,
    range_step_yd: float = 25.0,
) -> list[TrajectoryPoint]:
    """Compute a trajectory table. Raises ValueError on bad inputs.

    drop_in follows JBM convention: relative to the line of sight (accounts
    for sight height and the barrel angle needed to zero at zero_range_yd),
    not raw drop below the bore axis.

    diameter_in/length_in/twist_in are all optional and only affect spin
    drift (folded into windage_in/windage_moa) -- leave twist_in at 0 to
    disable spin drift entirely (windage then reflects wind drift only).
    """
    if drag_model not in DRAG_TABLES:
        raise ValueError(f"drag_model must be one of {list(DRAG_TABLES)}, got {drag_model!r}")
    if bc <= 0:
        raise ValueError("Ballistic coefficient must be positive")
    if weight_gr <= 0 or muzzle_velocity_fps <= 0:
        raise ValueError("Weight and muzzle velocity must be positive")

    dm = DragModel(bc, DRAG_TABLES[drag_model], weight_gr, diameter_in, length_in)
    ammo = Ammo(dm, Unit.FPS(muzzle_velocity_fps))
    weapon = Weapon(
        sight_height=Unit.Inch(sight_height_in),
        twist=Unit.Inch(twist_in) if twist_in else None,
    )
    atmo = Atmo(
        altitude=Unit.Foot(altitude_ft),
        pressure=Unit.InHg(pressure_inhg) if pressure_inhg else None,
        temperature=Unit.Fahrenheit(temperature_f),
        humidity=humidity_pct,
    )
    winds = [Wind(velocity=Unit.MPH(wind_speed_mph), direction_from=Unit.Degree(wind_direction_deg))] \
        if wind_speed_mph else []

    shot = Shot(
        ammo=ammo,
        atmo=atmo,
        weapon=weapon,
        winds=winds,
        look_angle=Unit.Degree(look_angle_deg),
    )

    calc = Calculator()
    calc.set_weapon_zero(shot, Unit.Yard(zero_range_yd))

    try:
        hit = calc.fire(
            shot,
            trajectory_range=Unit.Yard(max_range_yd),
            trajectory_step=Unit.Yard(range_step_yd),
            raise_range_error=False,
        )
    except RangeError as exc:
        raise ValueError(f"Could not compute trajectory: {exc}") from exc

    points: list[TrajectoryPoint] = []
    for p in hit:
        points.append(TrajectoryPoint(
            range_yd=p.distance >> Unit.Yard,
            time_s=p.time,
            velocity_fps=p.velocity >> Unit.FPS,
            mach=p.mach,
            drop_in=p.slant_height >> Unit.Inch,
            drop_moa=p.drop_angle >> Unit.MOA,
            windage_in=p.windage >> Unit.Inch,
            windage_moa=p.windage_angle >> Unit.MOA,
            energy_ftlb=p.energy >> Unit.FootPound,
        ))
    return points


if __name__ == "__main__":
    # Self-check: py_ballisticcalc ships its own reference example
    # (py_ballisticcalc/example.py) computed in metric/Celsius units. This
    # reproduces the *same* shot in this wrapper's imperial inputs (precise
    # unit conversions below) and should match its printed output exactly,
    # to the decimal, at every 100 m mark:
    #   0m: -2.4in @ 2750.0fps/2821ft-lb   500m: -69.9in @ 1740.9fps/1130ft-lb
    #   100m: 0.0in @ 2527.6fps/2383ft-lb  600m: -116.3in @ 1566.7fps/916ft-lb
    #   200m: -4.2in @ 2315.4fps/2000ft-lb 700m: -179.6in @ 1400.4fps/732ft-lb
    #   300m: -16.1in @ 2114.1fps/1667ft-lb 800m: -264.3in @ 1243.6fps/577ft-lb
    #   400m: -37.4in @ 1923.1fps/1379ft-lb 900m: -376.0in @ 1102.4fps/453ft-lb
    #                                      1000m: -521.6in @ 1030.5fps/396ft-lb
    # Verified matching exactly when this was written (py_ballisticcalc 2.3.1).
    rows = compute_trajectory(
        weight_gr=168, muzzle_velocity_fps=2750, bc=0.223, drag_model="G7",
        diameter_in=0.308, length_in=1.282,
        sight_height_in=6 / 2.54,          # 6 cm
        zero_range_yd=100 / 0.9144,        # 100 m
        altitude_ft=110 / 0.3048,          # 110 m
        pressure_inhg=29.8,
        temperature_f=15 * 9 / 5 + 32,     # 15 C
        humidity_pct=72,
        wind_speed_mph=2 / 1.466667,       # 2 fps (example's PreferredUnits.velocity was FPS)
        wind_direction_deg=90,
        max_range_yd=1000 / 0.9144,        # 1000 m
        range_step_yd=100 / 0.9144,        # 100 m steps
    )
    for r in rows:
        print(f"{r['range_yd'] * 0.9144:7.1f} m  drop={r['drop_in']:8.1f} in  "
              f"vel={r['velocity_fps']:7.1f} fps  e={r['energy_ftlb']:6.0f} ft-lb")
