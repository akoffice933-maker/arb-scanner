import asyncio
from typing import Optional
import aiohttp
from datetime import datetime
from config.settings import settings
from core.spread_calculator import SpreadOpportunity


class TelegramAlerter:
    """Клиент для отправки алертов в Telegram"""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = "https://api.telegram.org/bot"
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_delay = 0.5  # Задержка между сообщениями
        self._last_message_time = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание HTTP сессии"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Закрытие HTTP сессии"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _send_message(self, text: str, parse_mode: str = "HTML"):
        """
        Отправка сообщения в Telegram

        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML или Markdown)
        """
        if not self.bot_token or not self.chat_id:
            print("⚠️ Telegram credentials not configured")
            return

        # Rate limiting
        current_time = datetime.now().timestamp()
        if current_time - self._last_message_time < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay)

        url = f"{self.base_url}{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    self._last_message_time = datetime.now().timestamp()
                else:
                    error_data = await response.json()
                    print(f"❌ Telegram API error: {error_data}")
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")

    async def send_opportunity_alert(self, opportunity: SpreadOpportunity):
        """
        Отправка алерта об арбитражной возможности

        Args:
            opportunity: SpreadOpportunity
        """
        timestamp = datetime.fromtimestamp(opportunity.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        text = (
            f"🚀 <b>Arbitrage Opportunity Detected!</b>\n\n"
            f"🪙 <b>Token:</b> {opportunity.token_symbol}\n"
            f"⏰ <b>Time:</b> {timestamp}\n\n"
            f"📊 <b>Route:</b>\n"
            f"  Buy: {opportunity.buy_dex}\n"
            f"  Sell: {opportunity.sell_dex}\n\n"
            f"💰 <b>Prices:</b>\n"
            f"  Buy Price: ${opportunity.buy_price:.6f}\n"
            f"  Sell Price: ${opportunity.sell_price:.6f}\n\n"
            f"📈 <b>Spread:</b>\n"
            f"  Gross: {opportunity.spread_gross_percent:.2f}%\n"
            f"  Net: {opportunity.spread_net_percent:.2f}%\n\n"
            f"💵 <b>Estimated Profit:</b> ${opportunity.estimated_profit_usd:.2f}\n"
            f"⛽ <b>Gas + Tip:</b> ${opportunity.estimated_gas_usd:.2f}\n\n"
            f"📉 <b>Slippage:</b> {opportunity.slippage_percent:.2f}%\n"
            f"⏱️ <b>Lifetime:</b> {opportunity.lifetime_ms}ms\n"
            f"💧 <b>Liquidity:</b> ${opportunity.liquidity_available:,.0f}"
        )

        await self._send_message(text)

    async def send_scanner_status(self, status: dict):
        """
        Отправка статуса сканера

        Args:
            status: Словарь со статусом сканера
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        networks_info = ""
        for network in status.get("networks", []):
            rpc_status = network.get("rpc_status", {})
            networks_info += (
                f"\n<b>{network['name'].upper()}:</b>\n"
                f"  Active Node: {rpc_status.get('active_node', 'N/A')}\n"
                f"  Latency: {rpc_status.get('active_latency_ms', 0):.2f}ms\n"
                f"  Pools: {network.get('pools_count', 0)}\n"
            )

        text = (
            f"📊 <b>Scanner Status Report</b>\n\n"
            f"⏰ <b>Time:</b> {timestamp}\n"
            f"✅ <b>Running:</b> {status.get('running', False)}\n\n"
            f"<b>Networks:</b>{networks_info}"
        )

        await self._send_message(text)

    async def send_error_alert(self, error_type: str, error_message: str):
        """
        Отправка алерта об ошибке

        Args:
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        text = (
            f"❌ <b>Error Alert</b>\n\n"
            f"⏰ <b>Time:</b> {timestamp}\n"
            f"🔴 <b>Type:</b> {error_type}\n"
            f"📝 <b>Message:</b>\n"
            f"<code>{error_message}</code>"
        )

        await self._send_message(text)

    async def send_startup_notification(self):
        """Отправка уведомления о запуске сканера"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        text = (
            f"🚀 <b>Arbitrage Scanner Started!</b>\n\n"
            f"⏰ <b>Time:</b> {timestamp}\n"
            f"🌐 <b>Networks:</b> {', '.join(settings.TARGET_NETWORKS)}\n"
            f"💧 <b>Min Liquidity:</b> ${settings.MIN_LIQUIDITY_USD:,.0f}\n"
            f"📈 <b>Min Spread:</b> {settings.MIN_SPREAD_NET_PERCENT:.2f}%\n\n"
            f"✅ Scanner is now monitoring for opportunities!"
        )

        await self._send_message(text)

    async def send_shutdown_notification(self):
        """Отправка уведомления об остановке сканера"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        text = (
            f"🛑 <b>Arbitrage Scanner Stopped</b>\n\n"
            f"⏰ <b>Time:</b> {timestamp}\n\n"
            f"Scanner has been shut down."
        )

        await self._send_message(text)
