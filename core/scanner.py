import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
from infrastructure.rpc_manager import RPCManager
from core.pool_tracker import PoolTracker
from core.spread_calculator import SpreadCalculator, SpreadOpportunity
from storage.database import Database
from monitoring.metrics import Metrics
from config.settings import settings


class ArbitrageScanner:
    """Основной сканер арбитражных возможностей"""

    def __init__(self):
        self.solana_rpc: Optional[RPCManager] = None
        self.base_rpc: Optional[RPCManager] = None
        self.solana_pools: Optional[PoolTracker] = None
        self.base_pools: Optional[PoolTracker] = None
        self.spread_calculator = SpreadCalculator()
        self.db: Optional[Database] = None
        self.metrics: Optional[Metrics] = None
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._opportunity_cache: Dict[str, float] = {}  # Для расчёта lifetime

    async def start(self):
        """Запуск сканера"""
        print("🚀 Starting Arbitrage Scanner v3.0...")

        # Инициализация базы данных
        self.db = Database()
        await self.db.connect()

        # Инициализация метрик
        self.metrics = Metrics()
        await self.metrics.start()

        # Инициализация RPC для Solana
        if "solana" in settings.TARGET_NETWORKS:
            self.solana_rpc = RPCManager(
                [
                    settings.SOLANA_RPC_PRIMARY,
                    settings.SOLANA_RPC_SECONDARY,
                    settings.SOLANA_RPC_TERTIARY,
                ],
                "solana",
            )
            await self.solana_rpc.start()
            self.solana_pools = PoolTracker("solana")
            await self.solana_pools.start(await self.solana_rpc.get_client())
            print("✅ Solana RPC & Pool Tracker initialized")

        # Инициализация RPC для Base
        if "base" in settings.TARGET_NETWORKS:
            self.base_rpc = RPCManager(
                [settings.BASE_RPC_PRIMARY, settings.BASE_RPC_SECONDARY],
                "base",
            )
            await self.base_rpc.start()
            self.base_pools = PoolTracker("base")
            await self.base_pools.start(await self.base_rpc.get_client())
            print("✅ Base RPC & Pool Tracker initialized")

        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())
        print("✅ Scanner started")

    async def stop(self):
        """Остановка сканера"""
        print("🛑 Stopping Scanner...")
        self._running = False

        if self._scan_task:
            self._scan_task.cancel()

        if self.solana_pools:
            await self.solana_pools.stop()
        if self.base_pools:
            await self.base_pools.stop()
        if self.solana_rpc:
            await self.solana_rpc.stop()
        if self.base_rpc:
            await self.base_rpc.stop()
        if self.db:
            await self.db.disconnect()
        if self.metrics:
            await self.metrics.stop()

        print("✅ Scanner stopped")

    async def _scan_loop(self):
        """Основной цикл сканирования"""
        scan_count = 0
        start_time = time.time()

        while self._running:
            try:
                scan_start = time.perf_counter()

                # Сканирование Solana
                if self.solana_pools:
                    opportunities = await self._scan_network(
                        self.solana_pools, "solana"
                    )
                    for opp in opportunities:
                        await self._process_opportunity(opp)

                # Сканирование Base
                if self.base_pools:
                    opportunities = await self._scan_network(self.base_pools, "base")
                    for opp in opportunities:
                        await self._process_opportunity(opp)

                scan_count += 1
                scan_duration = (time.perf_counter() - scan_start) * 1000

                # Обновление метрик
                if self.metrics:
                    self.metrics.record_scan(scan_duration)

                # Логирование статуса каждые 60 секунд
                if scan_count % 30 == 0:
                    elapsed = time.time() - start_time
                    print(
                        f"📊 Scans: {scan_count}, Duration: {elapsed:.0f}s, "
                        f"Avg scan time: {scan_duration:.2f}ms"
                    )

                # Пауза между сканами (целевая частота ~2 скана в секунду)
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Scan error: {e}")
                await asyncio.sleep(1)

    async def _scan_network(
        self, pool_tracker: PoolTracker, network: str
    ) -> List[SpreadOpportunity]:
        """Сканирование одной сети"""
        opportunities = []
        pools = pool_tracker.get_all_pools()

        # Сравнение всех пар пулов для одного токена
        token_pools: Dict[str, List] = {}
        for pool in pools:
            if pool.liquidity_usd < settings.MIN_LIQUIDITY_USD:
                continue

            # Группировка по токену
            for token in [pool.token_a, pool.token_b]:
                if token not in token_pools:
                    token_pools[token] = []
                token_pools[token].append(pool)

        # Поиск спредов между пулами одного токена
        for token, pools_list in token_pools.items():
            if len(pools_list) < 2:
                continue

            for i, buy_pool in enumerate(pools_list):
                for sell_pool in pools_list[i + 1 :]:
                    if buy_pool.dex == sell_pool.dex:
                        continue  # Пропускаем одинаковые DEX

                    opportunity = self.spread_calculator.calculate_spread(
                        buy_pool=buy_pool.to_dict(),
                        sell_pool=sell_pool.to_dict(),
                        trade_amount_usd=10000,
                    )

                    if opportunity:
                        opportunity.lifetime_ms = self._calculate_lifetime(opportunity)
                        opportunities.append(opportunity)

        return opportunities

    def _calculate_lifetime(self, opportunity: SpreadOpportunity) -> int:
        """Расчёт времени жизни арбитражной возможности"""
        key = (
            f"{opportunity.token_symbol}_{opportunity.buy_pool}_{opportunity.sell_pool}"
        )
        current_time = time.time()

        if key in self._opportunity_cache:
            first_seen = self._opportunity_cache[key]
            lifetime_ms = int((current_time - first_seen) * 1000)
        else:
            self._opportunity_cache[key] = current_time
            lifetime_ms = 0

        # Очистка кэша для возможностей старше 5 секунд
        expired_keys = [
            k for k, v in self._opportunity_cache.items() if current_time - v > 5
        ]
        for k in expired_keys:
            del self._opportunity_cache[k]

        return lifetime_ms

    async def _process_opportunity(self, opportunity: SpreadOpportunity):
        """Обработка найденной арбитражной возможности"""
        # Логирование
        print(
            f"💡 Opportunity: {opportunity.token_symbol} | "
            f"{opportunity.buy_dex} → {opportunity.sell_dex} | "
            f"Spread: {opportunity.spread_net_percent:.2f}% | "
            f"Profit: ${opportunity.estimated_profit_usd:.2f} | "
            f"Lifetime: {opportunity.lifetime_ms}ms"
        )

        # Сохранение в базу данных
        if self.db:
            await self.db.save_opportunity(opportunity)

        # Обновление метрик
        if self.metrics:
            self.metrics.record_opportunity(opportunity)

        # Отправка алерта если спред выше порога
        if opportunity.spread_net_percent >= 1.0:  # Порог для алерта
            if self.metrics:
                await self.metrics.send_alert(opportunity)

    def get_status(self) -> Dict:
        """Получение статуса сканера"""
        status = {
            "running": self._running,
            "networks": [],
        }

        if self.solana_rpc:
            status["networks"].append(
                {
                    "name": "solana",
                    "rpc_status": self.solana_rpc.get_status(),
                    "pools_count": (
                        len(self.solana_pools.pools) if self.solana_pools else 0
                    ),
                }
            )

        if self.base_rpc:
            status["networks"].append(
                {
                    "name": "base",
                    "rpc_status": self.base_rpc.get_status(),
                    "pools_count": len(self.base_pools.pools) if self.base_pools else 0,
                }
            )

        return status
