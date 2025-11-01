# View logs (use service names)
docker compose logs -f ema_trading_bot
docker compose logs -f config_bot
docker compose logs -f  # Both containers

# Restart services (use service names)
docker compose restart ema_trading_bot
docker compose restart config_bot

# Execute commands inside containers (use container names)
docker exec ema_delta_trading_bot_avi_da_rsi_sma_test_two_way python -c "print('hello')"
docker exec trading_config_bot docker ps

# Check status
docker compose ps
docker ps  # Shows container names

# Stop/start
docker compose down
docker compose up -d