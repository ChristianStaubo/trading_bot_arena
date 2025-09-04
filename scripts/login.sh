#!/bin/bash
set -e

echo "[login.sh] Waiting for GUI to fully load..."
sleep 10

echo "[login.sh] Clicking 'IB API' button..."
xdotool mousemove 661 249 click 1
sleep 3

echo "[login.sh] Clicking 'Paper Trading' toggle..."
xdotool mousemove 615 301 click 1
sleep 0.5
xdotool mousemove 615 301 click 1
sleep 2

echo "[login.sh] Clicking into 'Username' field..."
xdotool mousemove 395 353 click 1
sleep 0.5
xdotool type "$TWS_USERID"
sleep 1

echo "[login.sh] Clicking into 'Password' field..."
xdotool mousemove 403 398 click 1
sleep 0.5
xdotool type "$TWS_PASSWORD"
sleep 1

echo "[login.sh] Clicking 'Log In'..."
xdotool mousemove 560 449 click 1

echo "[login.sh] Login sequence completed. Waiting for session to establish..."
