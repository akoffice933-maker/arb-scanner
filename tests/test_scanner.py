import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from core.spread_calculator import SpreadCalculator, SpreadOpportunity
from core.pool_tracker import PoolTracker, PoolInfo
from infrastructure.rpc_manager import RPCManager, RPCNode


class TestSpreadCalculator:
    """Тесты для калькулятора спреда"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.calculator = SpreadCalculator(sol_price_usd=150.0, eth_price_usd=3000.0)

    def test_calculate_spread_profitable(self):
        """Тест расчёта прибыльного спреда"""
        buy_pool = {
            "address": "pool1",
            "dex": "raydium",
            "token_a_symbol": "SOL",
            "price_a_per_b": 150.0,
            "fee_percent": 0.25,
            "liquidity_usd": 100000,
        }

        sell_pool = {
            "address": "pool2",
            "dex": "orca",
            "token_a_symbol": "SOL",
            "price_a_per_b": 152.0,
            "fee_percent": 0.30,
            "liquidity_usd": 100000,
        }

        opportunity = self.calculator.calculate_spread(buy_pool=buy_pool, sell_pool=sell_pool, trade_amount_usd=10000)

        assert opportunity is not None
        assert opportunity.spread_gross_percent > 0
        assert opportunity.estimated_profit_usd > 0

    def test_calculate_spread_unprofitable(self):
        """Тест расчёта убыточного спреда"""
        buy_pool = {
            "address": "pool1",
            "dex": "raydium",
            "token_a_symbol": "SOL",
            "price_a_per_b": 150.0,
            "fee_percent": 0.25,
            "liquidity_usd": 100000,
        }

        sell_pool = {
            "address": "pool2",
            "dex": "orca",
            "token_a_symbol": "SOL",
            "price_a_per_b": 149.0,  # Цена ниже, нет арбитража
            "fee_percent": 0.30,
            "liquidity_usd": 100000,
        }

        opportunity = self.calculator.calculate_spread(buy_pool=buy_pool, sell_pool=sell_pool, trade_amount_usd=10000)

        assert opportunity is None

    def test_calculate_spread_zero_price(self):
        """Тест с нулевой ценой"""
        buy_pool = {
            "address": "pool1",
            "dex": "raydium",
            "token_a_symbol": "SOL",
            "price_a_per_b": 0,
            "fee_percent": 0.25,
            "liquidity_usd": 100000,
        }

        sell_pool = {
            "address": "pool2",
            "dex": "orca",
            "token_a_symbol": "SOL",
            "price_a_per_b": 150.0,
            "fee_percent": 0.30,
            "liquidity_usd": 100000,
        }

        opportunity = self.calculator.calculate_spread(buy_pool=buy_pool, sell_pool=sell_pool, trade_amount_usd=10000)

        assert opportunity is None

    def test_update_token_prices(self):
        """Тест обновления цен токенов"""
        self.calculator.update_token_prices(sol_price=200.0, eth_price=3500.0)

        assert self.calculator.sol_price_usd == 200.0
        assert self.calculator.eth_price_usd == 3500.0

    def test_spread_opportunity_to_dict(self):
        """Тест конвертации SpreadOpportunity в словарь"""
        opportunity = SpreadOpportunity(
            timestamp=1234567890.0,
            token_symbol="SOL",
            buy_dex="raydium",
            sell_dex="orca",
            buy_pool="pool1",
            sell_pool="pool2",
            buy_price=150.0,
            sell_price=152.0,
            spread_gross_percent=1.33,
            spread_net_percent=0.5,
            estimated_profit_usd=50.0,
            estimated_tip_sol=0.001,
            estimated_gas_usd=0.15,
            slippage_percent=0.2,
            lifetime_ms=100,
            liquidity_available=100000,
        )

        data = opportunity.to_dict()

        assert data["token_symbol"] == "SOL"
        assert data["spread_gross_percent"] == 1.33
        assert data["estimated_profit_usd"] == 50.0


class TestPoolTracker:
    """Тесты для трекера пулов"""

    def test_pool_info_to_dict(self):
        """Тест конвертации PoolInfo в словарь"""
        from datetime import datetime

        pool_info = PoolInfo(
            address="58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
            dex="raydium",
            token_a="So11111111111111111111111111111111111111112",
            token_b="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            token_a_symbol="SOL",
            token_b_symbol="USDC",
            liquidity_usd=100000,
            price_a_per_b=150.0,
            price_b_per_a=0.0067,
            fee_percent=0.25,
            last_update=datetime.utcnow(),
        )

        data = pool_info.to_dict()

        assert data["dex"] == "raydium"
        assert data["token_a_symbol"] == "SOL"
        assert data["liquidity_usd"] == 100000

    def test_pool_tracker_initialization(self):
        """Тест инициализации PoolTracker"""
        tracker = PoolTracker(network="solana")

        assert tracker.network == "solana"
        assert len(tracker.pool_configs) > 0

    def test_pool_tracker_base_network(self):
        """Тест инициализации PoolTracker для Base"""
        tracker = PoolTracker(network="base")

        assert tracker.network == "base"
        assert tracker.pool_configs == PoolTracker.BASE_POOLS


class TestRPCManager:
    """Тесты для RPC менеджера"""

    @pytest.mark.asyncio
    async def test_rpc_node_creation(self):
        """Тест создания RPC ноды"""
        node = RPCNode("https://example.com/rpc", "test_node")

        assert node.url == "https://example.com/rpc"
        assert node.name == "test_node"
        assert node.is_healthy == True
        assert node.latency_ms == float("inf")

    @pytest.mark.asyncio
    async def test_rpc_manager_initialization(self):
        """Тест инициализации RPC менеджера"""
        rpc_urls = [
            "https://rpc1.example.com",
            "https://rpc2.example.com",
            "https://rpc3.example.com",
        ]

        manager = RPCManager(rpc_urls, "solana")

        assert len(manager.nodes) == 3
        assert manager.network == "solana"
        assert manager.active_node is None

    @pytest.mark.asyncio
    async def test_select_best_node(self):
        """Тест выбора лучшей ноды"""
        manager = RPCManager(["https://rpc.example.com"], "solana")

        # Симуляция данных о латентности
        manager.nodes[0].latency_ms = 50
        manager.nodes[0].is_healthy = True

        manager._select_best_node()

        assert manager.active_node is not None
        assert manager.active_node.name == "solana_0"

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Тест получения статуса RPC менеджера"""
        manager = RPCManager(["https://rpc.example.com"], "solana")
        manager.nodes[0].latency_ms = 50
        manager.nodes[0].is_healthy = True
        manager.active_node = manager.nodes[0]

        status = manager.get_status()

        assert status["network"] == "solana"
        assert status["active_node"] == "solana_0"
        assert status["active_latency_ms"] == 50


class TestIntegration:
    """Интеграционные тесты"""

    @pytest.mark.asyncio
    async def test_full_spread_calculation_flow(self):
        """Тест полного потока расчёта спреда"""
        calculator = SpreadCalculator(sol_price_usd=150.0)

        # Создаём тестовые пулы
        buy_pool = {
            "address": "pool1",
            "dex": "raydium",
            "token_a_symbol": "SOL",
            "price_a_per_b": 150.0,
            "fee_percent": 0.25,
            "liquidity_usd": 100000,
        }

        sell_pool = {
            "address": "pool2",
            "dex": "orca",
            "token_a_symbol": "SOL",
            "price_a_per_b": 153.0,
            "fee_percent": 0.30,
            "liquidity_usd": 100000,
        }

        # Рассчитываем спред
        opportunity = calculator.calculate_spread(buy_pool=buy_pool, sell_pool=sell_pool, trade_amount_usd=10000)

        assert opportunity is not None
        assert opportunity.token_symbol == "SOL"
        assert opportunity.buy_dex == "raydium"
        assert opportunity.sell_dex == "orca"
        assert opportunity.spread_net_percent > 0
        assert opportunity.estimated_profit_usd > 0

        # Конвертируем в словарь для сохранения
        data = opportunity.to_dict()
        assert "timestamp" in data
        assert "estimated_profit_usd" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
