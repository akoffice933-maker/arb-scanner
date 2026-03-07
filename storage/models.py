from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ArbitrageOpportunity(Base):
    """Модель для хранения арбитражных возможностей"""

    __tablename__ = "arbitrage_opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    network = Column(String(50), nullable=False)  # solana, base
    token_symbol = Column(String(20), nullable=False)
    token_address = Column(String(100), nullable=False)

    # Пулы
    buy_dex = Column(String(50), nullable=False)
    sell_dex = Column(String(50), nullable=False)
    buy_pool = Column(String(100), nullable=False)
    sell_pool = Column(String(100), nullable=False)

    # Цены
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)

    # Спреды
    spread_gross_percent = Column(Float, nullable=False)
    spread_net_percent = Column(Float, nullable=False)

    # Прибыль и расходы
    estimated_profit_usd = Column(Float, nullable=False)
    estimated_tip_sol = Column(Float, nullable=False)
    estimated_gas_usd = Column(Float, nullable=False)

    # Параметры
    slippage_percent = Column(Float, nullable=False)
    lifetime_ms = Column(Integer, nullable=False)
    liquidity_available = Column(Float, nullable=False)

    # Статус
    status = Column(String(20), default="detected")  # detected, executed, failed

    # Индексы для ускорения запросов
    __table_args__ = (
        Index("idx_timestamp", "timestamp"),
        Index("idx_token_symbol", "token_symbol"),
        Index("idx_network", "network"),
        Index("idx_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "network": self.network,
            "token_symbol": self.token_symbol,
            "token_address": self.token_address,
            "buy_dex": self.buy_dex,
            "sell_dex": self.sell_dex,
            "buy_pool": self.buy_pool,
            "sell_pool": self.sell_pool,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "spread_gross_percent": self.spread_gross_percent,
            "spread_net_percent": self.spread_net_percent,
            "estimated_profit_usd": self.estimated_profit_usd,
            "estimated_tip_sol": self.estimated_tip_sol,
            "estimated_gas_usd": self.estimated_gas_usd,
            "slippage_percent": self.slippage_percent,
            "lifetime_ms": self.lifetime_ms,
            "liquidity_available": self.liquidity_available,
            "status": self.status,
        }


class ScanMetric(Base):
    """Модель для хранения метрик сканирования (TimescaleDB hypertable)"""

    __tablename__ = "scan_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    network = Column(String(50), nullable=False)
    scan_duration_ms = Column(Float, nullable=False)
    pools_scanned = Column(Integer, default=0)
    opportunities_found = Column(Integer, default=0)
    rpc_latency_ms = Column(Float, nullable=False)

    __table_args__ = (Index("idx_time_network", "time", "network"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "time": self.time.isoformat() if self.time else None,
            "network": self.network,
            "scan_duration_ms": self.scan_duration_ms,
            "pools_scanned": self.pools_scanned,
            "opportunities_found": self.opportunities_found,
            "rpc_latency_ms": self.rpc_latency_ms,
        }


class RPCStatus(Base):
    """Модель для хранения статуса RPC нод"""

    __tablename__ = "rpc_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    network = Column(String(50), nullable=False)
    node_name = Column(String(100), nullable=False)
    latency_ms = Column(Float, nullable=False)
    is_healthy = Column(Integer, default=1)  # 1 = true, 0 = false
    error_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_rpc_timestamp", "timestamp"),
        Index("idx_rpc_network", "network"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "network": self.network,
            "node_name": self.node_name,
            "latency_ms": self.latency_ms,
            "is_healthy": bool(self.is_healthy),
            "error_count": self.error_count,
        }
