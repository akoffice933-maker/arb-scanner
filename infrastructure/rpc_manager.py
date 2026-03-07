import asyncio
import time
from typing import Optional, List, Dict, Any
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
import aiohttp
from config.settings import settings


class RPCNode:
    def __init__(self, url: str, name: str):
        self.url = url
        self.name = name
        self.client = AsyncClient(url, commitment=Confirmed)
        self.latency_ms: float = float('inf')
        self.is_healthy: bool = True
        self.last_check: float = 0
        self.error_count: int = 0

    async def check_latency(self) -> float:
        """Проверка пинга до ноды"""
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(
                    self.url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    await resp.json()
            self.latency_ms = (time.perf_counter() - start) * 1000
            self.is_healthy = True
            self.error_count = 0
        except Exception as e:
            self.is_healthy = False
            self.error_count += 1
            self.latency_ms = float('inf')
        self.last_check = time.time()
        return self.latency_ms

    async def get_slot(self) -> Optional[int]:
        """Получение текущего слота"""
        try:
            resp = await self.client.get_slot()
            return resp.value
        except:
            return None


class RPCManager:
    def __init__(self, rpc_urls: List[str], network: str = "solana"):
        self.network = network
        self.nodes: List[RPCNode] = [
            RPCNode(url, f"{network}_{i}") for i, url in enumerate(rpc_urls)
        ]
        self.active_node: Optional[RPCNode] = None
        self._health_check_task: Optional[asyncio.Task] = None

    async def start(self):
        """Запуск мониторинга здоровья нод"""
        await self._check_all_nodes()
        self._select_best_node()
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self):
        """Остановка мониторинга"""
        if self._health_check_task:
            self._health_check_task.cancel()
        for node in self.nodes:
            await node.client.close()

    async def _health_check_loop(self):
        """Периодическая проверка всех нод"""
        while True:
            await asyncio.sleep(10)  # Проверка каждые 10 секунд
            await self._check_all_nodes()
            self._select_best_node()

    async def _check_all_nodes(self):
        """Проверка всех нод параллельно"""
        tasks = [node.check_latency() for node in self.nodes]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _select_best_node(self):
        """Выбор ноды с минимальным пингом"""
        healthy_nodes = [n for n in self.nodes if n.is_healthy and n.latency_ms < 50]
        if healthy_nodes:
            self.active_node = min(healthy_nodes, key=lambda n: n.latency_ms)
        elif self.nodes:
            self.active_node = self.nodes[0]  # Fallback к первой ноде

    async def get_client(self) -> AsyncClient:
        """Получение активного клиента"""
        if not self.active_node or not self.active_node.is_healthy:
            await self._check_all_nodes()
            self._select_best_node()

        if not self.active_node:
            raise Exception("No healthy RPC nodes available")

        return self.active_node.client

    def get_current_latency(self) -> float:
        """Текущий пинг активной ноды"""
        return self.active_node.latency_ms if self.active_node else float('inf')

    def get_status(self) -> Dict[str, Any]:
        """Статус всех нод для мониторинга"""
        return {
            "network": self.network,
            "active_node": self.active_node.name if self.active_node else None,
            "active_latency_ms": self.get_current_latency(),
            "nodes": [
                {
                    "name": n.name,
                    "latency_ms": n.latency_ms,
                    "healthy": n.is_healthy,
                    "errors": n.error_count
                }
                for n in self.nodes
            ]
        }
