#!/usr/bin/env python3
"""
muse_lsl_rename_bridge.py

Reads two raw Muse LSL streams (both named "Muse", type "EEG") and republishes
new LSL streams with unique names (e.g., "Muse-07D2" and "Muse-FDCA").

You cannot rename an existing LSL stream in-place; this script republishes
a new stream with the same data and timestamps.

Run:
  conda activate muse
  python -u muse_lsl_rename_bridge.py
Stop:
  Ctrl+C
"""

import time
from typing import Dict, Optional, Tuple

from pylsl import resolve_byprop, StreamInlet, StreamInfo, StreamOutlet


# Map: original source_id -> new unique stream name you want
SOURCEID_TO_NEWNAME: Dict[str, str] = {
    "Muse4958F72E-7C39-0160-BF5F-CF3B502830A9": "Muse-07D2",
    "MuseAEA692BD-3F88-9724-A811-249F4450D2B3": "Muse-FDCA",
}

# Only relay this stream type (matches what you printed)
STREAM_TYPE = "EEG"

# Optional: only relay streams whose name matches this exactly (muselsl uses "Muse")
REQUIRE_NAME: Optional[str] = "Muse"


def make_outlet_from_source(src_info, new_name: str) -> StreamOutlet:
    """Create a StreamOutlet mirroring src_info but with a new name + unique source_id."""
    new_source_id = f"Renamed:{new_name}:{src_info.source_id()}"

    info = StreamInfo(
        name=new_name,
        type=src_info.type(),  # keep "EEG"
        channel_count=src_info.channel_count(),
        nominal_srate=src_info.nominal_srate(),
        channel_format=src_info.channel_format(),
        source_id=new_source_id,
    )

    # Helpful metadata for debugging
    desc = info.desc()
    desc.append_child_value("original_name", src_info.name())
    desc.append_child_value("original_type", src_info.type())
    desc.append_child_value("original_source_id", src_info.source_id())
    desc.append_child_value("original_uid", src_info.uid())
    desc.append_child_value("renamed_to", new_name)

    return StreamOutlet(info)


def discover_sources() -> Dict[str, object]:
    """Find candidate streams and return {source_id: StreamInfo} for the ones we care about."""
    streams = resolve_byprop("type", STREAM_TYPE, timeout=2)

    found: Dict[str, object] = {}
    for s in streams:
        if REQUIRE_NAME is not None and s.name() != REQUIRE_NAME:
            continue
        sid = s.source_id()
        if sid in SOURCEID_TO_NEWNAME:
            found[sid] = s
    return found


def main():
    print("=== Muse LSL Rename Bridge ===", flush=True)
    print("Looking for these source_ids:", flush=True)
    for k, v in SOURCEID_TO_NEWNAME.items():
        print(f"  {k}  ->  {v}", flush=True)
    print("", flush=True)

    relays: Dict[str, Tuple[StreamInlet, StreamOutlet, str]] = {}  # sid -> (inlet, outlet, new_name)

    try:
        while True:
            # Discover and attach any missing streams
            found = discover_sources()
            for sid, src_info in found.items():
                if sid in relays:
                    continue

                new_name = SOURCEID_TO_NEWNAME[sid]
                inlet = StreamInlet(src_info, recover=True)
                outlet = make_outlet_from_source(src_info, new_name)

                relays[sid] = (inlet, outlet, new_name)

                print(
                    f"[ADD] source_id='{sid}' name='{src_info.name()}' type='{src_info.type()}' "
                    f"-> republishing as name='{new_name}' (type='{src_info.type()}')",
                    flush=True,
                )

            # Forward samples (non-blocking)
            for sid, (inlet, outlet, new_name) in list(relays.items()):
                try:
                    sample, ts = inlet.pull_sample(timeout=0.0)
                    if ts:
                        outlet.push_sample(sample, ts)
                except Exception as e:
                    # If a headset disconnects, keep running; it should recover when it comes back.
                    print(f"[WARN] relay '{new_name}' (sid={sid}) error: {e}", flush=True)

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nStopping bridge.", flush=True)


if __name__ == "__main__":
    main()
