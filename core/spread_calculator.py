from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from config.settings import settings


@dataclass
class SpreadOpportunity:
    """Данные об арбитражной возможности"""
    timestamp: float
    token_symbol: str
    buy_dex: str
    sell_dex: str
    buy_pool: str
    sell_pool: str
    buy_price: float
    sell_price: float
    spread_gross_percent: float
    spread_net_percent: float
    estimated_profit_usd: float
    estimated_tip_sol: float
    estimated_gas_usd: float
    slippage_percent: float
    lifetime_ms: int
    liquidity_available: float

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "token_symbol": self.token_symbol,
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
            "liquidity_available": self.liquidity_available
        }


class SpreadCalculator:
    """Расчёт спреда с учётом всех комиссий"""

    def __init__(self, sol_price_usd: float = 150.0, eth_price_usd: float = 3000.0):
        self.sol_price_usd = sol_price_usd
        self.eth_price_usd = eth_price_usd

    def calculate_spread(
        self,
        buy_pool: Dict,
        sell_pool: Dict,
        trade_amount_usd: float = 10000
    ) -> Optional[SpreadOpportunity]:
        """
        Расчёт арбитражного спреда между двумя пулами

        Args:
            buy_pool: Данные пула для покупки
            sell_pool: Данные пула для продажи
            trade_amount_usd: Сумма сделки в USD

        Returns:
            SpreadOpportunity или None если спред невыгодный
        """
        # Цены
        buy_price = buy_pool["price_a_per_b"]  # Цена токена A в токене B
        sell_price = sell_pool["price_a_per_b"]

        if buy_price <= 0 or sell_price <= 0:
            return None

        # Gross спред (без учёта комиссий)
        spread_gross = ((sell_price - buy_price) / buy_price) * 100

        if spread_gross <= 0:
            return None  # Нет арбитража

        # Комиссии DEX
        dex_fee_buy = buy_pool.get("fee_percent", 0.25)
        dex_fee_sell = sell_pool.get("fee_percent", 0.25)
        total_dex_fee = dex_fee_buy + dex_fee_sell

        # Проскальзывание (упрощённая модель)
        liquidity = min(
            buy_pool.get("liquidity_usd", 100000),
            sell_pool.get("liquidity_usd", 100000)
        )
        slippage = (trade_amount_usd / liquidity) * 100 * 2  # Коэффициент 2 для безопасности

        # Газ и Tips
        gas_sol = 0.000005  # Solana базовый газ
        tip_sol = self._estimate_tip()  # Динамический тип
        total_gas_sol = gas_sol + tip_sol
        gas_usd = total_gas_sol * self.sol_price_usd

        # Net спред
        spread_net = spread_gross - total_dex_fee - slippage - (gas_usd / trade_amount_usd * 100)

        # Прибыль
        profit_usd = (trade_amount_usd * spread_net / 100) - gas_usd

        if spread_net < settings.MIN_SPREAD_NET_PERCENT or profit_usd <= 0:
            return None

        return SpreadOpportunity(
            timestamp=datetime.utcnow().timestamp(),
            token_symbol=buy_pool["token_a_symbol"],
            buy_dex=buy_pool["dex"],
            sell_dex=sell_pool["dex"],
            buy_pool=buy_pool["address"],
            sell_pool=sell_pool["address"],
            buy_price=buy_price,
            sell_price=sell_price,
            spread_gross_percent=spread_gross,
            spread_net_percent=spread_net,
            estimated_profit_usd=profit_usd,
            estimated_tip_sol=tip_sol,
            estimated_gas_usd=gas_usd,
            slippage_percent=slippage,
            lifetime_ms=0,  # Будет рассчитано сканером
            liquidity_available=liquidity
        )

    def _estimate_tip(self) -> float:
        """Оценка текущего tip floor (в реальности нужно получать из Jito API)"""
        # Заглушка - в production получать через Jito API
        return settings.TIP_FLOOR_SOL

    def update_token_prices(self, sol_price: float, eth_price: float):
        """Обновление цен нативных токенов"""
        self.sol_price_usd = sol_price
        self.eth_price_usd = eth_price
