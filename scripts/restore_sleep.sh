#!/bin/bash

# Restore normal sleep settings after trading

echo "💤 Restoring normal sleep settings..."

# Kill caffeinate processes
pkill caffeinate && echo "✅ Caffeinate stopped"

# Re-enable system sleep
sudo pmset -a disablesleep 0
echo "✅ System sleep re-enabled"

# Restore display sleep to reasonable default (10 minutes)
sudo pmset -a displaysleep 10 2>/dev/null || echo "Could not restore display sleep setting"

# Re-enable automatic graphics switching
sudo pmset -a gpuswitch 2 2>/dev/null || echo "GPU switching restored or not supported"

# Re-enable screen saver (5 minutes)
defaults -currentHost write com.apple.screensaver idleTime 300 2>/dev/null || true

echo "✅ Normal power management restored"
echo "✅ Display settings restored"
echo "💤 Your laptop can sleep again"