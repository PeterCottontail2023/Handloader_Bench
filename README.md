# Handloader Bench

A local, offline handload-tracking database and a JBM-Ballistics-style
trajectory calculator, combined into one app. Runs on Windows (a single
`.exe`, no installer) or from source on Linux/Mac.

```
Handloader_Bench/
├── launcher.py     # combined entry point
├── handloads/      # handload records tracker -- see handloads/README.md
└── ballistics/     # ballistics calculator -- see ballistics/README.md
```

## Download (Windows)

Grab the latest `HandloaderBench.exe` from this repo's **Releases** page.
It's a single portable file -- no installer, nothing else to download.

Windows will show a **"Windows protected your PC" / unknown publisher**
warning the first time you run it (SmartScreen -> More info -> Run anyway).
That's expected: the build is signed to prove it hasn't been tampered with
since it was built, but not with a certificate from a paid certificate
authority, which is what Windows requires to skip that warning entirely.

Your data (handload records) is saved to `%APPDATA%\HandloaderBench\` and
persists between launches and updates.

## Running from source (Linux/Mac)

Each tool runs standalone:

```
cd handloads && python3 app.py
cd ballistics && python3 app.py       # needs ballistics/vendor -- see its README
```

Or open both from one launcher window:

```
python3 launcher.py
```

## Building it yourself

See `BUILDING.md` for how the combined launcher and the Windows build/signing
pipeline work.

## License

MIT (`LICENSE`) for this repository's code. The built executable also
bundles a few third-party libraries under their own licenses -- see
`NOTICE.md`.
