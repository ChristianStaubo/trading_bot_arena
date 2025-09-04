import time
from ib_async import IB, util

ib = IB()
util.logToConsole("DEBUG")

print("Waiting before connect...")
time.sleep(1)

print("Connecting...")
ib.connect("127.0.0.1", 7497, clientId=1, timeout=30)

print("✅ Connected?", ib.isConnected())
ib.disconnect()
