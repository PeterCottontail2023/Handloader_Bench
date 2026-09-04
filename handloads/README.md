# Handloading Records

A local, offline tracker for handload development: firearms, load recipes,
and test results (velocity, groups, pressure signs). Pure Python standard
library -- SQLite for storage, Tkinter for the GUI. No network access, no
external dependencies, nothing leaves this machine.

## Setup

Tkinter is a separate OS package on Debian/Ubuntu-based systems:

```
sudo apt install -y python3-tk
```

## Run

```
python3 app.py
```

This creates `handloads.db` (SQLite) in this directory on first launch.

## Data model

- **firearms** -- rifle/pistol profiles (name, make, model, caliber, barrel
  length, twist rate, etc.). Loads optionally reference a firearm.
- **loads** -- one row per load recipe/test: case, primer, powder, bullet,
  seating depth, and results (velocity, SD/ES, group size, pressure signs,
  conditions, notes).
- **shot_strings** -- optional per-shot chronograph readings for a load. If
  entered in the GUI, average/SD/ES on the load are recomputed from these
  automatically.

See `schema.sql` for the full column list.

## Using the GUI

- **New load** / **Edit load** / **Delete load** -- manage load records.
  Double-click a row to edit it.
- **Manage firearms** -- add/edit/delete firearm profiles used in the load
  form's dropdown.
- **Search** -- filters by firearm name, caliber, bullet, powder, or notes.
- **Export CSV** -- dumps all load records (with computed firearm name) to a
  CSV file you choose, e.g. for a spreadsheet backup.

## Bulk import from an existing log

`db.py` exposes `add_firearm()` / `add_load()` / `set_shot_strings()` as a
plain Python API, so importing an existing load log (a PDF, spreadsheet, or
old notebook) is a matter of writing a short one-off script that parses your
source and calls those functions -- no GUI changes needed. A minimal example:

```python
import db

db.init_db()
rifle = db.add_firearm({"name": "My Rifle", "caliber": ".308 Winchester"})
db.add_load({
    "firearm_id": rifle, "status": "Proven",
    "bullet_weight_gr": 168, "bullet_type": "HPBT Match",
    "powder_type": "Varget", "charge_weight_gr": 42.5,
    "avg_velocity_fps": 2650, "notes": "...",
})
```

`set_shot_strings(load_id, [fps, fps, ...])` similarly records a chronograph
string and recomputes that load's average/SD/ES automatically.

## Backing up your data

Everything lives in `handloads.db`, a single SQLite file in this directory.
Copy it anywhere to back it up; open it with any SQLite browser
(e.g. `sqlite3 handloads.db` or DB Browser for SQLite) if you ever want to
query it directly.
