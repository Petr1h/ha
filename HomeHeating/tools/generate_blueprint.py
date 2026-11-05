"""Generate blueprints/automation/petr1h/heating_control.yaml.

Rooms are a dynamic list in the blueprint (object selector, add / remove in the GUI); this script only fills the
initial room list (names and weights below) into the template.
Usage:  python tools/generate_blueprint.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "blueprints" / "automation" / "petr1h" / "heating_control.yaml"

# (default name, default weight) - starting proposal, everything can be changed in the GUI
ROOMS = [
    ("Koupelka patro", 5), ("Kuchyň patro", 4), ("Patro pokoj", 5), ("Pracovna Petr", 6),
    ("Pracovna Zdeňka", 6), ("Chodba patro", 2), ("Chodba přízemí", 2), ("Koupelna přízemí", 5),
    ("Kuchyň", 6), ("Ložnice", 6), ("Obývák", 8), ("Předsíň", 2),
]


def main():
    template = (ROOT / "tools" / "heating_control.template.yaml").read_text(encoding="utf-8")
    defaults = "".join(
        f"            - name: {json.dumps(name, ensure_ascii=False)}\n"
        f"              trvs: []\n"
        f"              weight: {weight}\n"
        for name, weight in ROOMS
    )
    out = template.replace("@@ROOM_DEFAULTS@@\n", defaults)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"written {OUT} ({len(ROOMS)} default rooms)")


if __name__ == "__main__":
    main()
