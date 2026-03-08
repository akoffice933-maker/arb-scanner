"""
Liquidity Graph Engine

Tokens as nodes, pools as edges, log-prices as weights.
Bellman-Ford for negative cycle detection (arbitrage opportunities).

Target: >500k updates/sec, latency <80ms p95
"""
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import networkx as nx
import numpy as np


@dataclass
class Token:
    """Token node in the graph"""
    address: str
    symbol: str
    name: str
    decimals: int
    is_blacklisted: bool = False


@dataclass
class Pool:
    """Pool edge in the graph"""
    address: str
    dex: str
    token_a: str
    token_b: str
    liquidity_usd: float
    price_a_per_b: float
    price_b_per_a: float
    fee_percent: float
    last_update: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ArbitragePath:
    """Detected arbitrage opportunity (negative cycle)"""
    tokens: List[str]  # Path: A → B → C → A
    pools: List[str]  # Pool addresses
    profit_percent: float
    profit_usd: float
    hops: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "pools": self.pools,
            "profit_percent": self.profit_percent,
            "profit_usd": self.profit_usd,
            "hops": self.hops,
            "timestamp": self.timestamp.isoformat(),
        }


class LiquidityGraphEngine:
    """
    Graph-based liquidity tracker with cycle detection
    
    Architecture:
    - Tokens = nodes
    - Pools = edges (bidirectional)
    - Weights = -log(price) for negative cycle detection
    
    Algorithm: Bellman-Ford optimized for sparse graphs
    Complexity: O(V × E) per scan, where V=tokens, E=pools
    """
    
    def __init__(self, max_hop_count: int = 6, min_liquidity_usd: float = 50000):
        self.max_hop_count = max_hop_count
        self.min_liquidity_usd = min_liquidity_usd
        
        # Graph representation (NetworkX for flexibility, migrate to Rust later)
        self.graph = nx.DiGraph()
        
        # Caches
        self.tokens: Dict[str, Token] = {}
        self.pools: Dict[str, Pool] = {}
        self.token_blacklist: Set[str] = set()
        
        # Statistics
        self.scan_count = 0
        self.last_scan_time_ms = 0.0
        self.opportunities_found = 0
    
    def add_token(self, token: Token):
        """Add token node to graph"""
        if token.is_blacklisted or token.address in self.token_blacklist:
            return
        
        self.tokens[token.address] = token
        self.graph.add_node(token.address, token=token)
    
    def add_pool(self, pool: Pool):
        """Add pool edge to graph (bidirectional)"""
        if pool.liquidity_usd < self.min_liquidity_usd:
            return
        
        self.pools[pool.address] = pool
        
        # Add edges in both directions with log-price weights
        # Weight = -log(price) for negative cycle detection
        weight_a_to_b = -np.log(pool.price_a_per_b)
        weight_b_to_a = -np.log(pool.price_b_per_a)
        
        # Edge A → B
        self.graph.add_edge(
            pool.token_a,
            pool.token_b,
            weight=weight_a_to_b,
            pool_address=pool.address,
            dex=pool.dex,
            fee=pool.fee_percent,
        )
        
        # Edge B → A
        self.graph.add_edge(
            pool.token_b,
            pool.token_a,
            weight=weight_b_to_a,
            pool_address=pool.address,
            dex=pool.dex,
            fee=pool.fee_percent,
        )
    
    def remove_pool(self, pool_address: str):
        """Remove pool from graph"""
        if pool_address in self.pools:
            pool = self.pools[pool_address]
            # Remove both edges
            self.graph.remove_edge(pool.token_a, pool.token_b)
            self.graph.remove_edge(pool.token_b, pool.token_a)
            del self.pools[pool_address]
    
    def detect_arbitrage_opportunities(self) -> List[ArbitragePath]:
        """
        Detect arbitrage opportunities using Bellman-Ford
        
        Returns:
            List of ArbitragePath objects
        """
        opportunities = []
        
        # Run Bellman-Ford from each node (optimized for sparse graphs)
        # In production: use Johnson's algorithm or custom Rust implementation
        for source in list(self.graph.nodes())[:100]:  # Limit to 100 sources for performance
            try:
                # Find negative cycles
                cycle = nx.negative_edge_cycle(self.graph, weight="weight")
                if cycle:
                    # Extract cycle path
                    path = self._extract_cycle_path(source)
                    if path and len(path) <= self.max_hop_count + 1:
                        opp = self._create_opportunity(path)
                        if opp and opp.profit_percent > 0.1:  # Min 0.1% profit
                            opportunities.append(opp)
                            self.opportunities_found += 1
            except nx.NetworkXUnbounded:
                # Negative cycle exists
                path = self._extract_cycle_path(source)
                if path and len(path) <= self.max_hop_count + 1:
                    opp = self._create_opportunity(path)
                    if opp and opp.profit_percent > 0.1:
                        opportunities.append(opp)
                        self.opportunities_found += 1
            except Exception:
                continue
        
        self.scan_count += 1
        return opportunities
    
    def _extract_cycle_path(self, source: str) -> Optional[List[str]]:
        """Extract cycle path from source"""
        # Use Bellman-Ford predecessor to reconstruct cycle
        try:
            _, predecessors = nx.single_source_bellman_ford_path_length(
                self.graph, source, weight="weight"
            )
            
            # Reconstruct path (simplified, production needs full implementation)
            path = [source]
            current = source
            for _ in range(self.max_hop_count):
                if current in predecessors:
                    current = predecessors[current]
                    path.append(current)
                    if current == source:
                        break
                else:
                    break
            
            if len(path) > 2 and path[-1] == source:
                return path
        except Exception:
            pass
        
        return None
    
    def _create_opportunity(self, path: List[str]) -> Optional[ArbitragePath]:
        """Create ArbitragePath from cycle"""
        if len(path) < 3:
            return None
        
        # Calculate profit
        total_weight = 0.0
        pools_used = []
        
        for i in range(len(path) - 1):
            token_a = path[i]
            token_b = path[i + 1]
            
            # Get edge data
            edge_data = self.graph.get_edge_data(token_a, token_b)
            if edge_data:
                total_weight += edge_data["weight"]
                pools_used.append(edge_data["pool_address"])
        
        # Profit = exp(-total_weight) - 1
        profit_percent = (np.exp(-total_weight) - 1) * 100
        
        if profit_percent <= 0:
            return None
        
        # Estimate profit in USD (simplified, production uses simulation)
        profit_usd = profit_percent * 100  # Assume $100 trade size
        
        return ArbitragePath(
            tokens=path,
            pools=pools_used,
            profit_percent=profit_percent,
            profit_usd=profit_usd,
            hops=len(path) - 2,
        )
    
    async def update_pool(self, pool: Pool):
        """Update pool data (real-time)"""
        start_time = datetime.utcnow()
        
        # Update existing or add new
        self.add_pool(pool)
        
        # Track latency
        self.last_scan_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    def get_statistics(self) -> dict:
        """Get graph statistics"""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "tokens": len(self.tokens),
            "pools": len(self.pools),
            "scan_count": self.scan_count,
            "last_scan_time_ms": self.last_scan_time_ms,
            "opportunities_found": self.opportunities_found,
        }
