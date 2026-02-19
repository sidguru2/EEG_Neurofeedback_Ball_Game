# EEG Ball Game

A two-player competitive game controlled by EEG brain signals using Muse headsets. Players compete by achieving a relaxed mental state (measured via theta/beta bandpower ratio), with the ball moving toward the opponent's goal when they are more relaxed.

## Overview

This project creates an interactive game where two players wearing Muse EEG headsets compete by controlling a ball on screen. The game uses theta/beta bandpower ratio as a relaxation metric - the more relaxed player (lower ratio) moves the ball toward their opponent's goal. The first player to get the ball into their opponent's goalpost wins.

## Prerequisites

- Two Muse EEG headsets (Muse-FDCA and Muse-07D2)
- Python 3.x
- [muselsl](https://github.com/alexandrebarachant/muse-lsl) - For connecting to Muse headsets
- [Neuropype](https://www.neuropype.io/) - For EEG signal processing and bandpower calculation
- [pylsl](https://github.com/labstreaminglayer/liblsl-Python) - Lab Streaming Layer Python library
- tkinter (usually included with Python)
- PIL/Pillow - For image handling

## Setup

1. Install required Python packages:
```bash
pip install muselsl pylsl pillow
```

2. Ensure your Muse headsets are paired and ready to connect.

3. Configure Neuropype to:
   - Receive the renamed LSL streams from `muse_relay_rename.py`
   - Process the EEG signals
   - Calculate theta/beta bandpower ratio
   - Output streams named `Muse-FDCA_band` and `Muse-07D2_band` with the ratio values

## Usage

### Step 1: Turn on Muse Headsets

Power on both Muse headsets and ensure they are in pairing mode.

### Step 2: Start LSL Streams

Run the bash script to connect to both headsets and start LSL streams:

```bash
./run_eeg_game.sh
```

This script will:
- List available Muse devices
- Start streaming from both headsets (`Muse-FDCA` and `Muse-07D2`) in the background
- Launch `muse_relay_rename.py` to give each stream a unique identifier

The script will continue running until you stop it (Ctrl+C), at which point it will automatically stop the Muse streams.

### Step 3: Process Signals with Neuropype

In Neuropype:
1. Connect to the renamed LSL streams (`Muse-07D2` and `Muse-FDCA`)
2. Configure signal processing pipeline to calculate theta/beta bandpower ratio
3. Output processed streams with names:
   - `Muse-FDCA_band` (for Player 1)
   - `Muse-07D2_band` (for Player 2)

These streams should output single float values representing the theta/beta ratio.

### Step 4: Launch the Game

Run the game application:

```bash
python game.py
```

The game window will open with:
- **Left panel**: Player 1 status and real-time theta/beta ratio values
- **Center**: Game field with goalposts and moving ball/logo
- **Right panel**: Player 2 status and real-time theta/beta ratio values

### Step 5: Play

1. Click **"Scan & Bind Players"** to connect to the processed LSL streams
2. Wait for both players to be detected (you'll see "Found player stream ✅" for both)
3. Click **"Start"** to begin the game
4. Players compete by achieving a relaxed mental state - the more relaxed player (lower theta/beta ratio) moves the ball toward their opponent's goal
5. First player to get the ball into their opponent's goalpost wins!

## Game Functionality

### How It Works

- The game continuously reads theta/beta bandpower ratio values from both players
- Every second (configurable via `TICK_MS`), the game compares the latest values from both players
- **If Player 1's ratio < Player 2's ratio**: Ball moves left (toward Player 2's goal)
- **If Player 2's ratio < Player 1's ratio**: Ball moves right (toward Player 1's goal)
- **If ratios are equal**: No movement

### Game Controls

- **Scan & Bind Players**: Scans for available LSL streams and connects to the player streams
- **Start/Stop**: Starts or pauses the game
- **Reset**: Resets the game to initial state, clears connections, and re-centers the ball

### Game Features

- Real-time display of theta/beta ratio values for both players
- Visual feedback showing which player is currently "winning" (ball position)
- Automatic win detection when ball touches a goalpost
- Failsafe timer (30 seconds) that ends the game if no winner is determined
- Window resizing support with automatic repositioning of game elements

## Testing Without Hardware

To test the game without actual EEG hardware, you can use the mock scripts:

### Terminal 1: Mock Player 1
```bash
python mockp1.py
```

### Terminal 2: Mock Player 2
```bash
python mockp2.py
```

### Terminal 3: Run Game
```bash
python game.py
```

The mock scripts generate random values between 0.0 and 1.0 every 2 seconds, simulating the theta/beta ratio streams. This allows you to test the game mechanics without needing Muse headsets or Neuropype.

## File Descriptions

- **`run_eeg_game.sh`**: Bash script that starts both Muse streams and launches the relay rename script
- **`muse_relay_rename.py`**: Reads raw Muse LSL streams and republishes them with unique names (`Muse-07D2` and `Muse-FDCA`) so they can be distinguished
- **`game.py`**: Main game application that connects to processed LSL streams and displays the competitive game interface
- **`mockp1.py`**: Mock LSL stream generator for Player 1 (testing purposes)
- **`mockp2.py`**: Mock LSL stream generator for Player 2 (testing purposes)
- **`check.py`**: Utility script to list all available LSL streams (useful for debugging)

## Configuration

You can modify these constants in `game.py` to adjust game behavior:

- `SCAN_SETTLE_SEC`: Time to wait before scanning for streams (default: 2 seconds)
- `MOVE_PIXELS`: Number of pixels the ball moves per comparison (default: 10)
- `TICK_MS`: How often the game compares values and moves the ball (default: 1000ms)
- `FAILSAFE_MS`: Maximum game duration before automatic end (default: 30000ms / 30 seconds)

## Troubleshooting

- **Streams not found**: Ensure Neuropype is running and outputting streams with the exact names `Muse-FDCA_band` and `Muse-07D2_band`
- **Muse connection issues**: Check that headsets are powered on and in range. Use `muselsl list` to verify detection
- **Game not starting**: Make sure both player streams are detected before clicking "Start"
- **Ball not moving**: Verify that both streams are outputting values (check the value displays in the side panels)

## Notes

- The game expects LSL streams with single-channel float32 values representing theta/beta bandpower ratio
- Lower values indicate higher relaxation (which moves the ball toward opponent's goal)
- The game uses a queue-based system to ensure each value is consumed exactly once, preventing lag or missed updates
