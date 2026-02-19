import time
from pylsl import resolve_streams

print("Resolving all EEG streams (may take a few seconds)...\n")
time.sleep(2)

streams = resolve_streams()

print(f"Found {len(streams)} EEG stream(s):\n")
for s in streams:
    print(f"Name: {s.name()}")
    print(f"  Type: {s.type()}")
    print(f"  Source ID: {s.source_id()}")
    print("-" * 40)
