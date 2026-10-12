from __future__ import annotations

from collections import defaultdict

from flask import Flask, render_template

from cloud_logging import read_cosmos_events


app = Flask(__name__)


@app.route("/")
def dashboard():
    events, source = read_cosmos_events()
    grouped = defaultdict(list)
    for event in events:
        grouped[event["compartment_id"]].append(event)

    summaries = []
    for compartment_id, compartment_events in sorted(grouped.items()):
        latest = sorted(compartment_events, key=lambda item: item["timestamp"])[-1]
        summaries.append(
            {
                "compartment_id": compartment_id,
                "event_count": len(compartment_events),
                "latest_event": latest["event_type"],
                "has_tamper": any(event["event_type"] == "TAMPER" for event in compartment_events),
                "chain_valid": all(event.get("chain_valid", False) for event in compartment_events),
            }
        )

    ordered_events = sorted(events, key=lambda item: item["timestamp"], reverse=True)
    return render_template(
        "dashboard.html",
        source=source,
        summaries=summaries,
        events=ordered_events,
    )


if __name__ == "__main__":
    app.run(debug=False)
