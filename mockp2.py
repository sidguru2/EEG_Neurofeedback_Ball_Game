import time
import random
from pylsl import StreamInfo, StreamOutlet

def main():
    # name: Player2, type: EEG, source_id: player2_mock
    info = StreamInfo(
        name="Muse-FDCA_band",
        type="EEG",
        channel_count=1,
        nominal_srate=0.0,          # irregular / event-like (we'll push once per second)
        channel_format="float32",
        source_id=""
    )

    outlet = StreamOutlet(info)
    print("✅ LSL Stream started: for player 2")

    while True:
        v = random.random()  # 0.0 to 1.0
        outlet.push_sample([v])
        print(f"Player2 -> {v:.6f}")
        time.sleep(2.0)

if __name__ == "__main__":
    main()
