#!/bin/bash

# Absolute path of this script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PLIST_NAME="com.monitor.offers.plist"
SRC_PLIST="$DIR/$PLIST_NAME"
DEST_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=== Installing Gift Card Offer Monitor Daemon ==="

# 1. Check if source plist exists
if [ ! -f "$SRC_PLIST" ]; then
    echo "Error: Source file $SRC_PLIST not found."
    exit 1
fi

# 2. Copy plist to User's LaunchAgents directory
echo "Copying plist to LaunchAgents..."
cp "$SRC_PLIST" "$DEST_PLIST"
chmod 644 "$DEST_PLIST"

# 3. Unload agent if it is already loaded
echo "Unloading existing daemon if loaded..."
launchctl unload "$DEST_PLIST" 2>/dev/null

# 4. Load the new agent
echo "Loading launch daemon..."
if launchctl load "$DEST_PLIST"; then
    echo "Success! Launch daemon loaded and active."
else
    echo "Error: Failed to load launch daemon."
    exit 1
fi

echo ""
echo "=== Daemon is Active ==="
echo "The Deal monitor will run continuously in the background."
echo "You can check output logs at:"
echo "  Stdout: $DIR/stdout.log"
echo "  Stderr: $DIR/stderr.log"
echo ""
echo "To start the daemon manually or trigger a reload, run:"
echo "  launchctl start com.monitor.offers"
echo ""
