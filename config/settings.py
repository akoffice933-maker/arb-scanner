import os
from pydantic import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # === INFRASTRUCTURE ===
    ENVIRONMENT: str = "production"

    # Solana RPC (3 ноды для failover)
    SOLANA_RPC_PRIMARY: str = "https://mainnet.helius-rpc.com/?api-key=XXX"
    SOLANA_RPC_SECONDARY: str = "https://solana-mainnet.g.alchemy.com/v2/XXX"
    SOLANA_RPC_TERTIARY: str = "https://mainnet.triton.one/rpc/XXX"

    # Base RPC
    BASE_RPC_PRIMARY: str = "https://base-mainnet.g.alchemy.com/v2/XXX"
    BASE_RPC_SECONDARY: str = "https://base-mainnet.quicknode.com/XXX"

    # Jito
    JITO_UUID: str = "your-jito-uuid"
    JITO_AUTH_KEYPAIR: str = "path/to/keypair.json"
    SHREDSTREAM_ENDPOINT: str = "mainnet.block-engine.jito.wtf"

    # === DATABASE ===
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/arb_scanner"
    TIMESCALE_ENABLED: bool = True

    # === SCANNER SETTINGS ===
    TARGET_NETWORKS: List[str] = ["solana", "base"]  # Можно отключить одну сеть
    MIN_LIQUIDITY_USD: float = 50000  # Мин. ликвидность пула
    MIN_SPREAD_NET_PERCENT: float = 0.15  # Мин. спред net для логирования
    MAX_SLIPPAGE_PERCENT: float = 2.0  # Макс. проскальзывание
    RPC_TIMEOUT_SECONDS: float = 5.0
    RPC_MAX_RETRIES: int = 3

    # === TIP SETTINGS ===
    MAX_TIP_PERCENT_OF_PROFIT: float = 30.0  # Не платить больше 30% от прибыли
    TIP_FLOOR_SOL: float = 0.001  # Мин. тип в SOL

    # === ALERTS ===
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # === METRICS ===
    PROMETHEUS_PORT: int = 9090

    class Config:
        env_file = ".env"


settings = Settings()
