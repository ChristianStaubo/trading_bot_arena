# Trading Bot Arena

A modular trading bot with FastAPI backend and separate development/production environments.

## 🏗️ Project Structure

```
project/
├── api/                    # FastAPI backend
│   ├── Dockerfile         # API container build
│   └── entrypoint.sh      # API startup script
├── bot/                   # Trading bot logic (runs on host)
│   ├── Dockerfile         # Bot container build (not used in dev)
│   └── entrypoint.sh      # Bot startup script (for prod)
├── docker-compose.yml     # Points to dev config
├── docker-compose.dev.yml # Development (API + Postgres only)
├── docker-compose.prod.yml# Production (API + bot containers)
├── .env                   # Development environment
├── .env.prod              # Production environment
├── start_all.sh           # Development startup (host bot)
└── start_all_prod.sh      # Production startup (containerized)
```

## 🚀 Quick Start

### Development (Local with Host Bot)

The development setup runs the API and database in Docker containers, but runs the trading bot directly on the host machine for easier debugging and development.

```bash
# Starts IB Gateway, API + Database containers, and bot on host
./start_all.sh
```

This will:

1. Login to IB Gateway automatically
2. Start API and PostgreSQL in Docker containers
3. Run the trading bot directly on the host VM
4. Monitor all services and provide status updates

### Production (Digital Ocean)

```bash
# Full production startup (IB Gateway + containers)
./start_all_prod.sh

# Or manually build and deploy production containers
docker compose -f docker-compose.prod.yml up -d --build
```

## 📝 Environment Files

### `.env` (Development)

- Local database credentials
- IB Gateway settings for local testing
- Bot runs on host with localhost connections

### `.env.prod` (Production)

- External database URL (managed service)
- Production IB Gateway credentials
- Bot runs in container

## 🔧 Services

### Development Mode (Host Bot)

- **API**: FastAPI backend in Docker container
- **Postgres**: Local database container (port 5433)
- **Bot**: Runs directly on host VM (easier debugging)
  - Connects to containerized database via localhost:5433
  - Connects to containerized API via localhost:8000
  - Connects to IB Gateway on localhost

### Production Mode (Containerized)

- **API**: FastAPI backend container
- **Bot**: Trading bot service container
- **Database**: External managed database (not containerized)
- **IB Gateway**: Runs on host machine

## 🔄 Development Workflow

### Starting Development Environment

```bash
./start_all.sh
```

### Monitoring Services

```bash
# Check overall status (done automatically by start_all.sh)
docker compose -f docker-compose.dev.yml ps

# View API/Database logs
docker compose -f docker-compose.dev.yml logs -f

# View bot logs (running on host)
tail -f bot/logs/main.log

# Check API health
curl http://localhost:8000/api/v1/health
```

### Stopping Services

Press `Ctrl+C` in the terminal running `start_all.sh`, or:

```bash
# Stop Docker services
docker compose -f docker-compose.dev.yml down

# Stop bot if running separately
pkill -f "bot.py"
```

## 📚 Usage Examples

```bash
# Development (host bot mode)
./start_all.sh                                    # Full stack startup
docker compose -f docker-compose.dev.yml up -d    # API + DB only
docker compose -f docker-compose.dev.yml logs -f  # View container logs
docker compose -f docker-compose.dev.yml down     # Stop containers

# Production (containerized)
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml down
```

## 🐛 Troubleshooting

### Bot Issues

- Bot logs: `bot/logs/main.log`
- Check IB Gateway connection
- Verify environment variables are loaded correctly

### API Issues

- API logs: `docker compose -f docker-compose.dev.yml logs api`
- Health check: `curl http://localhost:8000/api/v1/health`

### Database Issues

- DB logs: `docker compose -f docker-compose.dev.yml logs postgres`
- Connect directly: `psql -h localhost -p 5433 -U [username] [database]`

## 🤖 Multiple Bot Support

The trading bot now supports running multiple bots in parallel using multiprocessing:

### Single Bot (Development)

```bash
# Default: runs one EURUSD bot
./start_all.sh
```

### Multiple Bots

```bash
# Just run the main bot script - it imports configs automatically
./start_all.sh

# Or run directly
cd bot
uv run bot.py
```

### Bot Configuration

Each bot requires:

- Unique `client_id` for IBKR connection (auto-assigned)
- Symbol and exchange configuration
- Strategy path and settings
- Risk management parameters

To add/modify bots, edit `bot/multi_bot_config.py` in the `get_development_bot_configs()` function.

### Monitoring Multiple Bots

- Each bot logs to its own file in `bot/logs/`
- Process isolation ensures one bot failure doesn't affect others
- Graceful shutdown with `Ctrl+C` stops all bots
- Individual bot status visible in console output
