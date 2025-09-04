# Trading Bot Infrastructure

This project is a modular trading bot setup with a FastAPI backend, a Dockerized architecture, and a host-managed login flow for IB Gateway. It is designed for reliability, simplicity, and clear separation of concerns.

---

## 🏗️ Project Structure

/
├── api/ # FastAPI backend for logging trades/signals
├── bot/ # Trading bot logic (1 strategy per bot)
├── docker-compose.yml # Orchestrates API, bot, and DB containers
├── pyproject.toml # Unified dependency config (uv-compatible)
├── uv.lock # Locked dependency versions
├── start_all.sh # Host-managed startup script

markdown
Copy
Edit

---

## 🚀 How It Works

### 1. **FastAPI Backend** (`/api`)

- Handles logging for trade signals, executed trades, and health checks
- Runs in a Docker container (`trading_bot_api`)
- Communicates with Postgres (also containerized)
- Serves endpoints for internal monitoring and debugging

### 2. **Trading Bot** (`/bot`)

- Executes one strategy per process
- Connects to IBKR via `ib-async`
- Submits logs to the API
- Runs inside a container (`trading_bot`)

### 3. **IB Gateway & Login Flow**

- IB Gateway is **installed and launched directly on the host machine** (not inside Docker)
- Auto-login is handled via a Python script using `pyautogui` and `pyotp`
- This script:
  - Starts IB Gateway if it's not already running
  - Performs GUI login automation
  - Can retry if login fails or IB Gateway crashes

---

## 🧪 Startup Flow

All services are orchestrated via the `start_all.sh` script:

1. Starts the IB Gateway (host)
2. Runs the auto-login script to authenticate via GUI
3. Launches the full Docker stack (API + bot + DB)

```bash
./start_all.sh
🐳 Docker Services
The docker-compose.yml file defines and launches:

trading_bot_api – FastAPI backend

trading_bot_postgres – Postgres database

trading_bot (coming soon) – Trading bot service(s)

bash
Copy
Edit
docker compose up -d --build
🧼 Notes
macOS-only dependencies (e.g. pyobjc, pyautogui) are marked with sys_platform == 'darwin' in pyproject.toml to avoid Linux build failures.

Only the API and bot run in Docker; the IB Gateway and login automation must run on the host due to GUI/system-level requirements.


```
