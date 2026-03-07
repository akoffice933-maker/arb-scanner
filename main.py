import asyncio
import signal
import sys
from datetime import datetime
from core.scanner import ArbitrageScanner
from config.settings import settings
from monitoring.alerts import TelegramAlerter


class ScannerService:
    """Сервис для управления жизненным циклом сканера"""

    def __init__(self):
        self.scanner = ArbitrageScanner()
        self.alerter = TelegramAlerter()
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Запуск сервиса"""
        print("=" * 60)
        print("🚀 ARBITRAGE SCANNER v3.0")
        print("=" * 60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Networks: {', '.join(settings.TARGET_NETWORKS)}")
        print(f"💧 Min Liquidity: ${settings.MIN_LIQUIDITY_USD:,.0f}")
        print(f"📈 Min Spread: {settings.MIN_SPREAD_NET_PERCENT:.2f}%")
        print("=" * 60)

        # Отправка уведомления о запуске
        await self.alerter.send_startup_notification()

        # Регистрация обработчиков сигналов
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )

        # Запуск сканера
        await self.scanner.start()

        # Ожидание сигнала завершения
        await self._shutdown_event.wait()

    async def shutdown(self):
        """Корректное завершение работы"""
        print("\n🛑 Shutdown initiated...")

        # Отправка уведомления об остановке
        await self.alerter.send_shutdown_notification()

        # Остановка сканера
        await self.scanner.stop()

        # Закрытие алертера
        await self.alerter.close()

        # Сигнал о завершении
        self._shutdown_event.set()

        print("✅ Shutdown complete")


async def main():
    """Точка входа"""
    service = ScannerService()

    try:
        await service.start()
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await service.alerter.send_error_alert("FatalError", str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
