"""
AME v3.0 Configuration

Hedge-fund grade settings for MEV arbitrage system.
"""
from pydantic import BaseSettings
from typing import List, Optional, Dict
import os


class AMESettings(BaseSettings):
    """
    Advanced MEV Arbitrage Engine Configuration
    
    Targets:
    - Latency: <30-80ms p95
    - Throughput: >500k updates/sec
    - Profit Accuracy: >97%
    """
    
    # ===================================================================
    # INFRASTRUCTURE
    # ===================================================================
    
    ENVIRONMENT: str = "production"  # production/development/testing
    
    # Solana RPC (Multi-RPC failover)
    SOLANA_RPC_PRIMARY: str = "https://mainnet.helius-rpc.com/?api-key=XXX"
    SOLANA_RPC_SECONDARY: str = "https://solana-mainnet.g.alchemy.com/v2/XXX"
    SOLANA_RPC_TERTIARY: str = "https://mainnet.triton.one/rpc/XXX"
    
    # Base RPC
    BASE_RPC_PRIMARY: str = "https://base-mainnet.g.alchemy.com/v2/XXX"
    BASE_RPC_SECONDARY: str = "https://base-mainnet.quicknode.com/XXX"
    
    # Jito ShredStream (Solana MEV)
    JITO_UUID: str = "your-jito-uuid"
    JITO_AUTH_KEYPAIR: str = "/app/keypairs/jito.json"
    SHREDSTREAM_ENDPOINT: str = "mainnet.block-engine.jito.wtf"
    
    # Flashbots (Base MEV)
    FLASHBOTS_RELAY_URL: str = "https://relay.flashbots.net"
    FLASHBOTS_AUTH_KEY: str = "your-flashbots-key"
    
    # ===================================================================
    # PERFORMANCE TARGETS
    # ===================================================================
    
    # Latency targets (milliseconds)
    TARGET_LATENCY_P50_MS: float = 30.0
    TARGET_LATENCY_P95_MS: float = 80.0
    TARGET_LATENCY_P99_MS: float = 150.0
    
    # Throughput targets (updates/sec)
    TARGET_THROUGHPUT_UPDATES_PER_SEC: int = 500000
    
    # ===================================================================
    # LIQUIDITY GRAPH
    # ===================================================================
    
    # Graph settings
    MAX_HOP_COUNT: int = 6  # Maximum swaps in arbitrage path
    MIN_LIQUIDITY_USD: float = 50000  # Minimum pool liquidity
    GRAPH_REBUILD_INTERVAL_SEC: int = 60  # Rebuild graph every N seconds
    
    # Token blacklist (honeypots, scams)
    TOKEN_BLACKLIST: List[str] = [
        "blacklisted_token_1",
        "blacklisted_token_2",
    ]
    
    # ===================================================================
    # STRATEGY LAYER
    # ===================================================================
    
    # Enabled strategies
    ENABLED_STRATEGIES: List[str] = [
        "triangular",
        "cross_dex",
        "backrun",
        # "liquidation",  # High risk
        # "jit_liquidity",  # Advanced
    ]
    
    # Strategy-specific settings
    TRIANGULAR_MIN_PROFIT_PERCENT: float = 0.1
    CROSS_DEX_MIN_PROFIT_PERCENT: float = 0.15
    BACKRUN_MIN_PROFIT_PERCENT: float = 1.0
    LIQUIDATION_MIN_PROFIT_PERCENT: float = 5.0
    
    # ===================================================================
    # PROFIT & RISK MODEL
    # ===================================================================
    
    # Minimum net profit threshold (after all costs)
    MIN_NET_PROFIT_PERCENT: float = 0.15
    
    # Cost estimates
    ESTIMATED_DEX_FEE_PERCENT: float = 0.25  # Average DEX fee
    ESTIMATED_SLIPPAGE_PERCENT: float = 0.2  # Expected slippage
    ESTIMATED_GAS_SOL: float = 0.000005  # Solana gas
    ESTIMATED_TIP_SOL: float = 0.001  # Jito tip floor
    
    # MEV haircut (competition buffer)
    MEV_HAIRCUT_PERCENT: float = 10.0  # Reduce profit by 10% for competition
    
    # ===================================================================
    # OPPORTUNITY SCORING
    # ===================================================================
    
    # Scoring weights
    SCORING_PROFIT_WEIGHT: float = 1.0
    SCORING_SUCCESS_PROB_WEIGHT: float = 0.5
    SCORING_LATENCY_RISK_WEIGHT: float = 0.3
    
    # Minimum score for execution
    MIN_OPPORTUNITY_SCORE: float = 100.0
    
    # ===================================================================
    # CAPITAL ALLOCATION
    # ===================================================================
    
    # Total capital available
    TOTAL_CAPITAL_USD: float = 50000.0
    
    # Allocation limits
    MAX_CAPITAL_PER_OPP_PERCENT: float = 20.0  # Max 20% per opportunity
    MAX_CAPITAL_PER_TOKEN_PERCENT: float = 30.0  # Max 30% per token
    MIN_TRADE_SIZE_USD: float = 1000.0  # Minimum trade size
    
    # Optimization settings
    OPTIMIZATION_METHOD: str = "newton"  # newton/grid_search
    
    # ===================================================================
    # OPPORTUNITY QUEUE
    # ===================================================================
    
    # Queue settings
    QUEUE_MAX_SIZE: int = 1000  # Max opportunities in queue
    QUEUE_BATCH_SIZE: int = 10  # Process N opps per batch
    QUEUE_TTL_MS: int = 5000  # Opportunity expires after 5 seconds
    
    # Scheduler settings
    SCHEDULER_INTERVAL_MS: int = 100  # Run scheduler every 100ms
    SCHEDULER_MAX_CONCURRENT: int = 3  # Max concurrent executions
    
    # ===================================================================
    # PORTFOLIO MANAGEMENT
    # ===================================================================
    
    # Risk constraints
    MAX_DAILY_LOSS_PERCENT: float = 5.0  # Stop if loss > 5%
    MAX_DRAWDOWN_PERCENT: float = 10.0  # Stop if drawdown > 10%
    MAX_EXPOSURE_PERCENT: float = 80.0  # Max capital deployed
    
    # Rebalancing
    REBALANCE_INTERVAL_MIN: int = 60  # Rebalance portfolio every hour
    
    # ===================================================================
    # TIP BIDDING & MEV COMPETITION
    # ===================================================================
    
    # Tip optimization
    TIP_BIDDING_ENABLED: bool = True
    TIP_MAX_PERCENT_OF_PROFIT: float = 30.0  # Max 30% of profit as tip
    TIP_FLOOR_SOL: float = 0.001  # Minimum tip
    TIP_CEILING_SOL: float = 0.05  # Maximum tip
    
    # Competition estimation
    COMPETITION_ESTIMATOR_ENABLED: bool = True
    COMPETITION_HIGH_MULTIPLIER: float = 2.0  # 2x tip in high competition
    COMPETITION_MEDIUM_MULTIPLIER: float = 1.5  # 1.5x in medium
    
    # ===================================================================
    # KILL-SWITCH RISK SYSTEM
    # ===================================================================
    
    KILL_SWITCH_ENABLED: bool = True
    
    # Triggers
    KILL_SWITCH_DAILY_LOSS_LIMIT: float = 5.0  # Stop at 5% daily loss
    KILL_SWITCH_GAS_SPIKE_MULTIPLIER: float = 2.0  # Pause if gas > 2x avg
    KILL_SWITCH_RPC_TIMEOUT_SEC: int = 60  # Failover after 60s outage
    KILL_SWITCH_BUNDLE_FAIL_RATE: float = 50.0  # Pause if > 50% fail
    KILL_SWITCH_LATENCY_P95_MS: float = 200.0  # Pause if p95 > 200ms
    
    # Cooldown
    KILL_SWITCH_COOLDOWN_MIN: int = 5  # Wait 5 min after trigger
    
    # ===================================================================
    # HISTORICAL ALPHA ANALYSIS
    # ===================================================================
    
    # Backtesting settings
    BACKTEST_ENABLED: bool = True
    BACKTEST_DAYS: int = 30  # Analyze last 30 days
    BACKTEST_MIN_SAMPLES: int = 100  # Minimum samples for analysis
    
    # Metrics
    ALPHA_METRICS: List[str] = [
        "profit_distribution",
        "win_rate",
        "avg_edge",
        "sharpe_ratio",
        "max_drawdown",
    ]
    
    # ===================================================================
    # DATABASE & CACHE
    # ===================================================================
    
    # PostgreSQL (TimescaleDB)
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/ame_v3"
    TIMESCALE_ENABLED: bool = True
    
    # Redis (cache/queue)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_SEC: int = 300  # 5 minutes
    
    # ===================================================================
    # MONITORING & TELEMETRY
    # ===================================================================
    
    # Prometheus
    PROMETHEUS_PORT: int = 9090
    METRICS_ENABLED: bool = True
    
    # Grafana
    GRAFANA_URL: str = "http://localhost:3000"
    GRAFANA_DASHBOARD_ID: str = "ame-v3-main"
    
    # Telegram alerts
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_ALERT_THRESHOLD_USD: float = 100.0  # Alert if profit > $100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "/app/logs/ame_v3.log"
    
    # ===================================================================
    # EXECUTION SETTINGS
    # ===================================================================
    
    # Bundle settings
    BUNDLE_MAX_RETRIES: int = 3
    BUNDLE_TIMEOUT_SEC: int = 30
    BUNDLE_USE_FLASHLOAN: bool = True  # Use flashloans for capital efficiency
    
    # Simulation
    SIMULATION_ENABLED: bool = True  # Simulate before execution
    SIMULATION_ERROR_THRESHOLD: float = 3.0  # Max 3% error vs real
    
    # ===================================================================
    # SECURITY
    # ===================================================================
    
    # Wallet settings
    SIM_ONLY_WALLET: bool = True  # Use sim-only wallet in testing
    MAINNET_WALLET_ADDRESS: Optional[str] = None
    
    # Secrets
    ENCRYPTION_KEY: Optional[str] = None  # For encrypting sensitive data
    
    # Audit
    BYTECODE_AUDIT_REQUIRED: bool = True  # Require audit before mainnet
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = AMESettings()
