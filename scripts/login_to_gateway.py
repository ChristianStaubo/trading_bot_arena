import pyautogui
import time
import subprocess
import pyotp
import os
import psutil
import socket
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def verify_ibkr_connection():
    """Final health test to verify IB Gateway is accepting API connections"""
    try:
        from ib_async import IB  # Using ib_async since that's what we have
        print("🔍 Running final IBKR connection health test...")
        
        # Determine correct port
        is_live_account = os.getenv("IS_LIVE_ACCOUNT", "false").lower() == "true"
        port = 7497 if is_live_account else 7497
        
        ib = IB()
        ib.connect("127.0.0.1", port, clientId=42)  # Use unique test client ID
        print("✅ Final connection test passed - IB Gateway is ready!")
        ib.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Final connection test failed: {e}")
        print("💡 IB Gateway may need more time or manual intervention")
        return False

def is_ib_gateway_running():
    """Check if IB Gateway is currently running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'java' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'ibgateway' in cmdline.lower() or 'gateway' in cmdline.lower():
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def is_ib_gateway_logged_in():
    """Check if IB Gateway is running and logged in by testing API connection"""
    try:
        # Determine the correct port based on account type
        is_live_account = os.getenv("IS_LIVE_ACCOUNT", "false").lower() == "true"
        port = 4001 if is_live_account else 4002  # Live: 4001, Paper: 4002
        
        # Try to connect to the IB Gateway API port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 second timeout
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        # If connection successful, IB Gateway is logged in
        return result == 0
        
    except Exception as e:
        print(f"🔍 Connection test failed: {e}")
        return False

def start_ib_gateway():
    """Start IB Gateway using the macOS app"""
    gateway_app = "/Users/user/Applications/IB Gateway 10.30/IB Gateway 10.30.app"
    trader_workstation_app = "/Users/user/Applications/Trader Workstation/Trader Workstation.app"
    
    if not os.path.exists(gateway_app):
        print(f"❌ IB Gateway not found at: {gateway_app}")
        return False
    
    try:
        print("🚀 Starting IB Gateway...")
        subprocess.Popen(['open', gateway_app])
        
        # Wait for it to start
        print("⏳ Waiting for IB Gateway to start...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(3)  # 3x longer wait (was 1 second)
            if is_ib_gateway_running():
                print("✅ IB Gateway is running!")
                return True
            print(f"   Waiting... ({i+1}/30)")
        
        print("⚠️ IB Gateway may not have started properly")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start IB Gateway: {e}")
        return False

def automated_login():
    """Perform automated login using pyautogui"""
    print("🔐 Starting automated login sequence...")
    
    username = os.getenv("IB_USERNAME")
    password = os.getenv("IB_PASSWORD")
    is_live_account = os.getenv("IS_LIVE_ACCOUNT", "false").lower() == "true"
    otp_secret = os.getenv("IB_OTP_SECRET")
    
    if not username or not password:
        print("❌ Please set IB_USERNAME and IB_PASSWORD in your .env file")
        return False
    
    # Check OTP setup based on account type
    if is_live_account:
        if not otp_secret:
            print("❌ IS_LIVE_ACCOUNT=true but no IB_OTP_SECRET provided!")
            print("💡 Live accounts require 2FA. Please add IB_OTP_SECRET to your .env file")
            return False
        
        # Test OTP secret validity for live accounts
        try:
            test_code = pyotp.TOTP(otp_secret).now()
            print(f"✅ OTP configured for LIVE account. Current code: {test_code}")
        except Exception as e:
            print(f"❌ Invalid OTP secret: {e}")
            print("💡 Your IB_OTP_SECRET should be a base32 string like: JBSWY3DPEHPK3PXP")
            return False
    else:
        print("📄 Paper trading account - no OTP required")
    
    # Wait a bit more for the login window to appear
    print("⏳ Waiting for login window...")
    time.sleep(30)  # 3x longer wait (was 10 seconds)
    
    try:
        # Click to focus the login window (adjust coordinates as needed)
        pyautogui.click(500, 400)
        time.sleep(3)  # 3x longer wait (was 1 second)
        
        # Login sequence
        print("📝 Entering username...")
        pyautogui.write(username)
        pyautogui.press('tab')
        
        print("📝 Entering password...")
        pyautogui.write(password)
        pyautogui.press('enter')
        
        # Handle 2FA only for live accounts
        if is_live_account and otp_secret:
            print("⏳ Waiting for 2FA prompt (LIVE account)...")
            time.sleep(9)  # 3x longer wait (was 3 seconds)
            
            # Generate and enter OTP
            code = pyotp.TOTP(otp_secret).now()
            print(f"📱 Entering 2FA code: {code}")
            pyautogui.write(code)
            pyautogui.press('enter')
        else:
            print("📄 Skipping 2FA for paper trading account")
        
        print("✅ Login sequence completed!")
        
        # NEW: Dismiss any post-login modals using recorded coordinates
        print("🎯 Dismissing post-login modals...")
        print("⏱️ Waiting 30 seconds for modals to appear...")
        time.sleep(30)  # 3x longer wait (was 10 seconds)
        
        # Use user's recorded click positions
        recorded_positions = [
            (287, 175),  # First modal button
            (850, 665),  # Second modal button
        ]
        
        for i, (x, y) in enumerate(recorded_positions, 1):
            try:
                print(f"   🖱️ Click {i}/2 at ({x}, {y})...")
                pyautogui.click(x, y)
                time.sleep(6)  # 3x longer wait (was 2 seconds)
            except Exception as e:
                print(f"   ⚠️ Click {i} failed: {e}")
        
        print("✅ Modal dismissal completed!")
        
        # NEW: Final connection health test
        print("🔍 Performing final IB Gateway connection verification...")
        time.sleep(15)  # Give IB Gateway extra time to be ready
        
        if verify_ibkr_connection():
            print("✅ IB Gateway is fully ready for API connections!")
            return True
        else:
            print("❌ IB Gateway connection test failed - may need manual intervention")
            return False
        
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return False

def main():
    """Main function"""
    account_type = "LIVE" if os.getenv("IS_LIVE_ACCOUNT", "false").lower() == "true" else "PAPER"
    
    print("🎯 IB Gateway Auto-Login Script")
    print("=" * 40)
    print(f"📊 Account Type: {account_type}")
    print("=" * 40)
    
    # Step 1: Check if IB Gateway is running
    if is_ib_gateway_running():
        print("✅ IB Gateway is already running")
        
        # Step 1.5: Check if already logged in
        if is_ib_gateway_logged_in():
            print("✅ IB Gateway is already logged in!")
            print(f"🎉 Success! IB Gateway ready for {account_type} account.")
            if account_type == "PAPER":
                print("💡 Your bot can connect to localhost:4002 (paper trading)")
            else:
                print("💡 Your bot can connect to localhost:4001 (LIVE trading)")
            return 0
        else:
            print("🔑 IB Gateway running but not logged in yet")
    else:
        print("🔍 IB Gateway not running, starting it...")
        if not start_ib_gateway():
            print("❌ Failed to start IB Gateway")
            return 1
    
    # Step 2: Perform automated login (only if not already logged in)
    print("\n" + "=" * 40)
    if automated_login():
        print(f"\n🎉 Success! IB Gateway logged in to {account_type} account.")
        if account_type == "PAPER":
            print("💡 Your bot can connect to localhost:4002 (paper trading)")
        else:
            print("💡 Your bot can connect to localhost:4001 (LIVE trading)")
    else:
        print("\n❌ Login failed. You may need to log in manually.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
