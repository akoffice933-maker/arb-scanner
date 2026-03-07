import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    start_http_server,
)
from config.settings import settings
from core.spread_calculator import SpreadOpportunity
from monitoring.alerts import TelegramAlerter


class Metrics:
    """Prometheus метрики для мониторинга сканера"""

    def __init__(self):
        self.registry = CollectorRegistry()

        # === Счётчики (Counters) ===
        self.scans_total = Counter(
            "arb_scanner_scans_total",
            "Total number of scans performed",
            ["network"],
            registry=self.registry,
        )

        self.opportunities_total = Counter(
            "arb_scanner_opportunities_total",
            "Total number of arbitrage opportunities detected",
            ["network", "token_symbol", "buy_dex", "sell_dex"],
            registry=self.registry,
        )

        self.alerts_total = Counter(
            "arb_scanner_alerts_total",
            "Total number of alerts sent",
            ["type"],
            registry=self.registry,
        )

        # === Гистограммы (Histograms) ===
        self.scan_duration = Histogram(
            "arb_scanner_scan_duration_seconds",
            "Time spent per scan",
            ["network"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry,
        )

        self.spread_distribution = Histogram(
            "arb_scanner_spread_percent",
            "Distribution of spread percentages",
            ["network"],
            buckets=(
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                1.5,
                2.0,
                3.0,
                5.0,
                10.0,
            ),
            registry=self.registry,
        )

        self.profit_distribution = Histogram(
            "arb_scanner_profit_usd",
            "Distribution of estimated profit",
            ["network"],
            buckets=(
                1,
                5,
                10,
                25,
                50,
                100,
                250,
                500,
                1000,
                2500,
                5000,
            ),
            registry=self.registry,
        )

        # === Гейджи (Gauges) ===
        self.rpc_latency = Gauge(
            "arb_scanner_rpc_latency_ms",
            "Current RPC latency in milliseconds",
            ["network", "node"],
            registry=self.registry,
        )

        self.active_pools = Gauge(
            "arb_scanner_active_pools",
            "Number of active liquidity pools being tracked",
            ["network", "dex"],
            registry=self.registry,
        )

        self.current_spread = Gauge(
            "arb_scanner_current_spread_percent",
            "Current best spread available",
            ["network", "token_symbol"],
            registry=self.registry,
        )

        self.scanner_running = Gauge(
            "arb_scanner_running",
            "Is the scanner running (1 = yes, 0 = no)",
            registry=self.registry,
        )

        # === Алертер ===
        self.alerter = TelegramAlerter()
        self._metrics_task: Optional[asyncio.Task] = None
        self._server_started = False

    async def start(self):
        """Запуск сервера метрик"""
        if not self._server_started:
            start_http_server(settings.PROMETHEUS_PORT, registry=self.registry)
            print(
                f"✅ Prometheus metrics server started on port {settings.PROMETHEUS_PORT}"
            )
            self._server_started = True

        self.scanner_running.set(1)

    async def stop(self):
        """Остановка сервера метрик"""
        self.scanner_running.set(0)
        # Prometheus не предоставляет async stop для start_http_server

    def record_scan(self, duration_ms: float, network: str = "solana"):
        """
        Запись метрик сканирования

        Args:
            duration_ms: Длительность скана в миллисекундах
            network: Сеть
        """
        duration_sec = duration_ms / 1000
        self.scans_total.labels(network=network).inc()
        self.scan_duration.labels(network=network).observe(duration_sec)

    def record_opportunity(
        self, opportunity: SpreadOpportunity, network: str = "solana"
    ):
        """
        Запись метрик арбитражной возможности

        Args:
            opportunity: SpreadOpportunity
            network: Сеть
        """
        self.opportunities_total.labels(
            network=network,
            token_symbol=opportunity.token_symbol,
            buy_dex=opportunity.buy_dex,
            sell_dex=opportunity.sell_dex,
        ).inc()

        self.spread_distribution.labels(network=network).observe(
            opportunity.spread_net_percent
        )

        self.profit_distribution.labels(network=network).observe(
            opportunity.estimated_profit_usd
        )

        # Обновляем текущий лучший спред
        self.current_spread.labels(
            network=network, token_symbol=opportunity.token_symbol
        ).set(opportunity.spread_net_percent)

    def update_rpc_latency(self, network: str, node: str, latency_ms: float):
        """
        Обновление метрик RPC латентности

        Args:
            network: Сеть
            node: Имя ноды
            latency_ms: Латентность в мс
        """
        self.rpc_latency.labels(network=network, node=node).set(latency_ms)

    def update_active_pools(self, network: str, dex: str, count: int):
        """
        Обновление количества активных пулов

        Args:
            network: Сеть
            dex: DEX
            count: Количество пулов
        """
        self.active_pools.labels(network=network, dex=dex).set(count)

    async def send_alert(self, opportunity: SpreadOpportunity):
        """
        Отправка алерта о значительной возможности

        Args:
            opportunity: SpreadOpportunity с высоким спредом
        """
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            try:
                await self.alerter.send_opportunity_alert(opportunity)
                self.alerts_total.labels(type="opportunity").inc()
            except Exception as e:
                print(f"❌ Failed to send alert: {e}")

    def get_metrics(self) -> str:
        """
        Получение всех метрик в формате Prometheus

        Returns:
            Строка с метриками
        """
        return generate_latest(self.registry).decode("utf-8")

    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса метрик

        Returns:
            Словарь со статусом
        """
        return {
            "prometheus_port": settings.PROMETHEUS_PORT,
            "server_running": self._server_started,
            "scanner_running": bool(self.scanner_running._value.get()),
        }
