# Third-party notices

The built Windows executable bundles the following libraries in addition to
this repository's own code (MIT, see `LICENSE`). This isn't legal advice --
just a good-faith list of what's embedded and under what license, compiled
from each package's published license as of the versions pinned in
`requirements.txt`; verify against the packages themselves (`pip show
<name>`, or their PyPI/GitHub pages) if it matters for your use.

## Directly depended on

- **[py_ballisticcalc](https://github.com/o-murphy/py-ballisticcalc)** --
  GNU Lesser General Public License v3.0 (LGPL-3.0). Source is on GitHub at
  the link above (unmodified from the version pinned in `requirements.txt`);
  see that project's `LICENSE` for the full text and your rights under it
  (including replacing the bundled copy with a modified version).
- **[matplotlib](https://matplotlib.org/)** -- matplotlib license (BSD-style,
  PSF-derived; see <https://matplotlib.org/stable/users/project/license.html>).

## Pulled in transitively (by matplotlib / py_ballisticcalc)

| Package | License |
|---|---|
| numpy | BSD-3-Clause |
| Pillow | MIT-CMU (PIL Software License) |
| contourpy | BSD-3-Clause |
| cycler | BSD-3-Clause |
| fonttools | MIT |
| kiwisolver | BSD-3-Clause |
| packaging | BSD-2-Clause / Apache-2.0 (dual) |
| pyparsing | MIT |
| python-dateutil | BSD-3-Clause / Apache-2.0 (dual) |
| six | MIT |
| typing_extensions | PSF-2.0 |
| Deprecated | MIT |
| wrapt | BSD-2-Clause |

## Not bundled

Python's standard library (`tkinter`, `sqlite3`, etc.) ships with Python
itself under the PSF License and isn't a separate bundled dependency.
