-- Handloading records database schema.
-- SQLite. Run automatically by db.py on first launch if tables are missing.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS firearms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,          -- nickname, e.g. "Remington 700 - deer rifle"
    make            TEXT,
    model           TEXT,
    caliber         TEXT NOT NULL,
    barrel_length_in REAL,
    twist_rate      TEXT,                   -- e.g. "1:10"
    action_type     TEXT,                   -- bolt, semi-auto, lever, revolver, etc.
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS loads (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    firearm_id          INTEGER REFERENCES firearms(id) ON DELETE SET NULL,
    date_loaded         TEXT,               -- ISO date, when the ammo was assembled
    date_tested         TEXT,               -- ISO date, when it was fired/chronographed
    caliber             TEXT,               -- redundant with firearm, useful if firearm untracked
    status              TEXT,               -- e.g. "Proven", "Untested", "Proven (Skeeter Skelton load)"

    -- Case
    case_mfr            TEXT,
    case_lot            TEXT,
    times_fired         INTEGER,            -- reload count for this brass

    -- Primer
    primer_mfr          TEXT,
    primer_type         TEXT,               -- e.g. "CCI 450 Small Rifle Magnum"

    -- Powder
    powder_mfr          TEXT,
    powder_type         TEXT,
    charge_weight_gr    REAL,

    -- Bullet
    bullet_mfr          TEXT,
    bullet_weight_gr    REAL,
    bullet_type         TEXT,               -- e.g. "SP", "HPBT Match"
    bullet_diameter_in  REAL,               -- bullet diameter, inches (for ballistics calc spin drift)
    bullet_length_in    REAL,               -- bullet length, inches (for ballistics calc spin drift)
    ballistic_coefficient REAL,             -- published or measured BC for bc_drag_model below
    bc_drag_model       TEXT,               -- "G1" or "G7"

    -- Seating / geometry
    coal_in             REAL,               -- cartridge overall length, inches
    seating_depth_note  TEXT,               -- e.g. "0.020 off lands"
    crimp               TEXT,               -- none / taper / roll (+ notes)

    -- Test results
    num_rounds          INTEGER,            -- rounds fired in this test batch
    avg_velocity_fps    REAL,
    sd_fps              REAL,
    es_fps              REAL,
    group_size_in       REAL,
    group_distance_yd   REAL,
    pressure_psi        REAL,               -- manufacturer-tested pressure (SAAMI/published data), not your own reading
    load_density_pct    REAL,               -- charge volume as % of case capacity, from published load data
    pressure_signs      TEXT,               -- your own subjective observations (flattened primers, etc.)
    temperature_f       REAL,
    weather_notes       TEXT,
    notes               TEXT,               -- structured/narrative description of the load
    comments            TEXT,               -- separate running personal commentary/opinion

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT
);

-- Optional per-shot chronograph readings for a load test.
-- If present, the GUI computes avg/SD/ES from these instead of the manual fields above.
CREATE TABLE IF NOT EXISTS shot_strings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    load_id         INTEGER NOT NULL REFERENCES loads(id) ON DELETE CASCADE,
    shot_number     INTEGER NOT NULL,
    velocity_fps    REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_loads_firearm ON loads(firearm_id);
CREATE INDEX IF NOT EXISTS idx_loads_caliber ON loads(caliber);
CREATE INDEX IF NOT EXISTS idx_shot_strings_load ON shot_strings(load_id);
