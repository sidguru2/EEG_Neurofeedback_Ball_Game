#!/bin/bash

echo "Starting EEG Ball Game Pipeline..."

# Go to project directory
cd /Users/sidabid09/Downloads/eeg_ball_game || exit

echo "Listing Muse devices..."
muselsl list

echo "Starting Muse streams..."

# Start both streams in background
muselsl stream --name Muse-FDCA &
PID1=$!

muselsl stream --name Muse-07D2 &
PID2=$!

echo "Starting relay script..."
python muse_relay_rename.py

echo "Relay script exited. Stopping Muse streams..."
kill $PID1 $PID2

echo "Done."
