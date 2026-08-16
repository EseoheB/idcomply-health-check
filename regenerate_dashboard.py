"""
regenerate_dashboard.py

Rebuilds index.html's three embedded data arrays (health, tickets,
rivetWeekly) from source CSVs, without touching any of the surrounding
HTML, CSS, or chart-drawing JavaScript. This is what lets the dashboard
itself refresh automatically, instead of staying a static snapshot.
"""

import csv
import json
import re

TEMPLATE_FILE = "index.html"
OUTPUT_FILE = "index.html"  # overwrites in place; GitHub Actions commits the change


def read_csv_as_records(path, numeric_fields=None, int_fields=None):
    numeric_fields = numeric_fields or []
    int_fields = int_fields or []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            for field in numeric_fields:
                if field in row and row[field] != "":
                    row[field] = float(row[field])
            for field in int_fields:
                if field in row and row[field] != "":
                    row[field] = int(float(row[field]))
            records.append(row)
        return records


def replace_js_array(html, var_name, data):
    """Finds `const <var_name> = [ ... ];` (allowing for the tickets
    variable's slightly different `const tickets = \n[ ... ];` layout)
    and replaces its contents with freshly serialized data, leaving
    everything else in the file untouched."""
    start_marker = f"const {var_name} ="
    start_idx = html.index(start_marker)
    bracket_start = html.index("[", start_idx)

    depth = 0
    i = bracket_start
    for i in range(bracket_start, len(html)):
        if html[i] == "[":
            depth += 1
        elif html[i] == "]":
            depth -= 1
            if depth == 0:
                break
    bracket_end = i  # index of the matching closing bracket

    # find the semicolon right after the closing bracket
    semicolon_idx = html.index(";", bracket_end)

    new_array_text = json.dumps(data, indent=2)
    before = html[:start_idx]
    after = html[semicolon_idx + 1:]
    return f"{before}const {var_name} = {new_array_text};{after}"


def main():
    health = read_csv_as_records(
        "health.csv",
        numeric_fields=["overall_pass_rate", "review_rate", "trend_pp",
                         "avg_resolve_hours", "reopen_rate", "standout_value"],
    )
    tickets = read_csv_as_records(
        "tickets.csv",
        numeric_fields=["time_to_resolve_hours"],
        int_fields=["index", "agent_touches", "sev_weight"],
    )
    rivet_weekly = read_csv_as_records(
        "rivet_weekly.csv",
        numeric_fields=["pass_rate_pct"],
    )

    with open(TEMPLATE_FILE) as f:
        html = f.read()

    html = replace_js_array(html, "health", health)
    html = replace_js_array(html, "tickets", tickets)
    html = replace_js_array(html, "rivetWeekly", rivet_weekly)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"Regenerated dashboard: {len(health)} customers, "
          f"{len(tickets)} tickets, {len(rivet_weekly)} weeks of Rivet data.")


if __name__ == "__main__":
    main()
