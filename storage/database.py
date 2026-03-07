import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from config.settings import settings
from storage.models import Base, ArbitrageOpportunity, ScanMetric, RPCStatus


class Database:
    """Асинхронный клиент для PostgreSQL с поддержкой TimescaleDB"""

    def __init__(self):
        self.engine = None
        self.async_session = None
        self._connected = False

    async def connect(self):
        """Подключение к базе данных"""
        try:
            # Создаём асинхронный движок
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,  # Включить для отладки SQL
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )

            # Создаём фабрику сессий
            self.async_session = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Создаём таблицы (в production лучше использовать миграции Alembic)
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Включаем TimescaleDB для метрик (если доступно)
            if settings.TIMESCALE_ENABLED:
                await self._enable_timescale()

            self._connected = True
            print(f"✅ Database connected: {settings.DATABASE_URL.split('@')[-1]}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    async def disconnect(self):
        """Отключение от базы данных"""
        if self.engine:
            await self.engine.dispose()
        self._connected = False
        print("✅ Database disconnected")

    async def _enable_timescale(self):
        """Включение расширения TimescaleDB"""
        try:
            async with self.async_session() as session:
                await session.execute(
                    "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"
                )
                await session.commit()

                # Преобразуем scan_metrics в hypertable
                await session.execute(
                    """
                    SELECT create_hypertable('scan_metrics', 'time', if_not_exists => TRUE)
                    """
                )
                await session.commit()
                print("✅ TimescaleDB enabled for scan_metrics")
        except Exception as e:
            print(f"⚠️ TimescaleDB setup failed (continuing without): {e}")

    async def save_opportunity(self, opportunity: Any) -> Optional[int]:
        """
        Сохранение арбитражной возможности

        Args:
            opportunity: SpreadOpportunity для сохранения

        Returns:
            ID сохранённой записи или None
        """
        if not self._connected:
            return None

        try:
            async with self.async_session() as session:
                db_opportunity = ArbitrageOpportunity(
                    timestamp=datetime.fromtimestamp(opportunity.timestamp),
                    network="solana",  # Определяется из контекста
                    token_symbol=opportunity.token_symbol,
                    token_address="",  # Нужно добавить в SpreadOpportunity
                    buy_dex=opportunity.buy_dex,
                    sell_dex=opportunity.sell_dex,
                    buy_pool=opportunity.buy_pool,
                    sell_pool=opportunity.sell_pool,
                    buy_price=opportunity.buy_price,
                    sell_price=opportunity.sell_price,
                    spread_gross_percent=opportunity.spread_gross_percent,
                    spread_net_percent=opportunity.spread_net_percent,
                    estimated_profit_usd=opportunity.estimated_profit_usd,
                    estimated_tip_sol=opportunity.estimated_tip_sol,
                    estimated_gas_usd=opportunity.estimated_gas_usd,
                    slippage_percent=opportunity.slippage_percent,
                    lifetime_ms=opportunity.lifetime_ms,
                    liquidity_available=opportunity.liquidity_available,
                )

                session.add(db_opportunity)
                await session.commit()
                await session.refresh(db_opportunity)
                return db_opportunity.id

        except Exception as e:
            print(f"❌ Failed to save opportunity: {e}")
            return None

    async def save_scan_metric(
        self,
        network: str,
        scan_duration_ms: float,
        pools_scanned: int,
        opportunities_found: int,
        rpc_latency_ms: float,
    ):
        """Сохранение метрики сканирования"""
        if not self._connected:
            return

        try:
            async with self.async_session() as session:
                metric = ScanMetric(
                    time=datetime.utcnow(),
                    network=network,
                    scan_duration_ms=scan_duration_ms,
                    pools_scanned=pools_scanned,
                    opportunities_found=opportunities_found,
                    rpc_latency_ms=rpc_latency_ms,
                )
                session.add(metric)
                await session.commit()

        except Exception as e:
            print(f"❌ Failed to save scan metric: {e}")

    async def save_rpc_status(
        self,
        network: str,
        node_name: str,
        latency_ms: float,
        is_healthy: bool,
        error_count: int,
    ):
        """Сохранение статуса RPC ноды"""
        if not self._connected:
            return

        try:
            async with self.async_session() as session:
                status = RPCStatus(
                    timestamp=datetime.utcnow(),
                    network=network,
                    node_name=node_name,
                    latency_ms=latency_ms,
                    is_healthy=1 if is_healthy else 0,
                    error_count=error_count,
                )
                session.add(status)
                await session.commit()

        except Exception as e:
            print(f"❌ Failed to save RPC status: {e}")

    async def get_recent_opportunities(
        self, limit: int = 100, network: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение последних арбитражных возможностей

        Args:
            limit: Максимальное количество записей
            network: Фильтр по сети (optional)

        Returns:
            Список словарей с данными
        """
        if not self._connected:
            return []

        try:
            async with self.async_session() as session:
                query = select(ArbitrageOpportunity).order_by(
                    ArbitrageOpportunity.timestamp.desc()
                ).limit(limit)

                if network:
                    query = query.where(ArbitrageOpportunity.network == network)

                result = await session.execute(query)
                opportunities = result.scalars().all()
                return [opp.to_dict() for opp in opportunities]

        except Exception as e:
            print(f"❌ Failed to get opportunities: {e}")
            return []

    async def get_statistics(
        self, hours: int = 24
    ) -> Dict[str, Any]:
        """
        Получение статистики за период

        Args:
            hours: Период в часах

        Returns:
            Словарь со статистикой
        """
        if not self._connected:
            return {}

        try:
            async with self.async_session() as session:
                since = datetime.utcnow() - timedelta(hours=hours)

                # Общее количество возможностей
                total_query = select(func.count(ArbitrageOpportunity.id)).where(
                    ArbitrageOpportunity.timestamp >= since
                )
                total_result = await session.execute(total_query)
                total = total_result.scalar()

                # Средняя прибыль
                avg_profit_query = select(
                    func.avg(ArbitrageOpportunity.estimated_profit_usd)
                ).where(ArbitrageOpportunity.timestamp >= since)
                avg_profit_result = await session.execute(avg_profit_query)
                avg_profit = avg_profit_result.scalar() or 0

                # Максимальный спред
                max_spread_query = select(
                    func.max(ArbitrageOpportunity.spread_net_percent)
                ).where(ArbitrageOpportunity.timestamp >= since)
                max_spread_result = await session.execute(max_spread_query)
                max_spread = max_spread_result.scalar() or 0

                return {
                    "period_hours": hours,
                    "total_opportunities": total,
                    "avg_profit_usd": round(avg_profit, 2),
                    "max_spread_percent": round(max_spread, 2),
                }

        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return {}

    async def cleanup_old_data(self, days: int = 7):
        """
        Очистка старых данных

        Args:
            days: Удалять данные старше этого количества дней
        """
        if not self._connected:
            return

        try:
            async with self.async_session() as session:
                since = datetime.utcnow() - timedelta(days=days)

                # Удаляем старые возможности
                from sqlalchemy import delete

                delete_query = delete(ArbitrageOpportunity).where(
                    ArbitrageOpportunity.timestamp < since
                )
                await session.execute(delete_query)

                # Удаляем старые метрики
                delete_metrics = delete(ScanMetric).where(ScanMetric.time < since)
                await session.execute(delete_metrics)

                await session.commit()
                print(f"✅ Cleaned up data older than {days} days")

        except Exception as e:
            print(f"❌ Failed to cleanup old data: {e}")
