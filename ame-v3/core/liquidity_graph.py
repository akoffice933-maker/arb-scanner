"""
Liquidity Graph Engine v2 — Multi-Pool Support + Real Cycle Detection

FIXED:
- Multiple pools per token pair (Raydium + Orca for SOL/USDC)
- Real Bellman-Ford cycle detection
- Proper path extraction
- Multi-hop arbitrage (up to 6 hops)

Target: >98% cycle detection accuracy, >500k updates/sec
"""
import asyncio
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np


@dataclass
class Token:
    """Token node in the graph"""
    address: str
    symbol: str
    name: str
    decimals: int
    is_blacklisted: bool = False
    
    def __hash__(self):
        return hash(self.address)
    
    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return self.address == other.address


@dataclass
class Pool:
    """Pool edge in the graph (FIXED: multiple pools per pair)"""
    address: str
    dex: str
    token_a: str
    token_b: str
    liquidity_usd: float
    price_a_per_b: float
    price_b_per_a: float
    fee_percent: float
    last_update: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "dex": self.dex,
            "token_a": self.token_a,
            "token_b": self.token_b,
            "liquidity_usd": self.liquidity_usd,
            "price_a_per_b": self.price_a_per_b,
            "price_b_per_a": self.price_b_per_a,
            "fee_percent": self.fee_percent,
            "last_update": self.last_update.isoformat(),
        }


@dataclass
class ArbitragePath:
    """Detected arbitrage opportunity (negative cycle)"""
    tokens: List[str]  # Path: A → B → C → A
    pools: List[str]  # Pool addresses
    dexes: List[str]  # DEX names
    profit_percent: float
    profit_usd: float
    hops: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "pools": self.pools,
            "dexes": self.dexes,
            "profit_percent": self.profit_percent,
            "profit_usd": self.profit_usd,
            "hops": self.hops,
            "timestamp": self.timestamp.isoformat(),
        }


class LiquidityGraphEngine:
    """
    Liquidity Graph Engine v2 — FIXED
    
    Key improvements:
    - Multiple pools per token pair
    - Real Bellman-Ford cycle detection
    - Proper path extraction
    - Multi-hop support (up to 6)
    """
    
    def __init__(self, max_hop_count: int = 6, min_liquidity_usd: float = 50000):
        self.max_hop_count = max_hop_count
        self.min_liquidity_usd = min_liquidity_usd
        
        # FIXED: Multi-pool support
        self.tokens: Dict[str, Token] = {}
        self.pools: Dict[str, Pool] = {}
        self.pools_by_pair: Dict[str, List[Pool]] = {}  # token_a-token_b -> [pools]
        
        # Graph adjacency list (FIXED: supports multiple edges)
        self.adjacency: Dict[str, List[Tuple[str, str, float]]] = {}  # token -> [(neighbor, pool_id, weight)]
        
        # Statistics
        self.scan_count = 0
        self.last_scan_time_ms = 0.0
        self.opportunities_found = 0
        self.cycles_detected = 0
    
    def add_token(self, token: Token):
        """Add token node to graph"""
        if token.is_blacklisted:
            return
        
        self.tokens[token.address] = token
        
        if token.address not in self.adjacency:
            self.adjacency[token.address] = []
    
    def add_pool(self, pool: Pool):
        """
        Add pool edge to graph (FIXED: multiple pools per pair)
        
        Creates bidirectional edges with log-price weights for
        Bellman-Ford negative cycle detection.
        """
        if pool.liquidity_usd < self.min_liquidity_usd:
            return
        
        # Store pool
        self.pools[pool.address] = pool
        
        # FIXED: Store in pools_by_pair (both directions)
        pair_key_ab = f"{pool.token_a}-{pool.token_b}"
        pair_key_ba = f"{pool.token_b}-{pool.token_a}"
        
        if pair_key_ab not in self.pools_by_pair:
            self.pools_by_pair[pair_key_ab] = []
        if pair_key_ba not in self.pools_by_pair:
            self.pools_by_pair[pair_key_ba] = []
        
        self.pools_by_pair[pair_key_ab].append(pool)
        self.pools_by_pair[pair_key_ba].append(pool)
        
        # Add to adjacency list (bidirectional)
        # Weight = -log(price) for negative cycle detection
        weight_a_to_b = -np.log(pool.price_a_per_b) if pool.price_a_per_b > 0 else float('inf')
        weight_b_to_a = -np.log(pool.price_b_per_a) if pool.price_b_per_a > 0 else float('inf')
        
        # Ensure tokens exist in adjacency
        if pool.token_a not in self.adjacency:
            self.adjacency[pool.token_a] = []
        if pool.token_b not in self.adjacency:
            self.adjacency[pool.token_b] = []
        
        # Add edges (FIXED: multiple edges per pair)
        self.adjacency[pool.token_a].append((pool.token_b, pool.address, weight_a_to_b))
        self.adjacency[pool.token_b].append((pool.token_a, pool.address, weight_b_to_a))
    
    def remove_pool(self, pool_address: str):
        """Remove pool from graph"""
        if pool_address not in self.pools:
            return
        
        pool = self.pools[pool_address]
        
        # Remove from pools
        del self.pools[pool_address]
        
        # Remove from pools_by_pair
        pair_key_ab = f"{pool.token_a}-{pool.token_b}"
        pair_key_ba = f"{pool.token_b}-{pool.token_a}"
        
        if pair_key_ab in self.pools_by_pair:
            self.pools_by_pair[pair_key_ab] = [
                p for p in self.pools_by_pair[pair_key_ab] if p.address != pool_address
            ]
        if pair_key_ba in self.pools_by_pair:
            self.pools_by_pair[pair_key_ba] = [
                p for p in self.pools_by_pair[pair_key_ba] if p.address != pool_address
            ]
        
        # Remove from adjacency list
        if pool.token_a in self.adjacency:
            self.adjacency[pool.token_a] = [
                (n, pid, w) for n, pid, w in self.adjacency[pool.token_a] if pid != pool_address
            ]
        if pool.token_b in self.adjacency:
            self.adjacency[pool.token_b] = [
                (n, pid, w) for n, pid, w in self.adjacency[pool.token_b] if pid != pool_address
            ]
    
    def detect_arbitrage_opportunities(self) -> List[ArbitragePath]:
        """
        Detect arbitrage opportunities using Bellman-Ford (FIXED: real algorithm)
        
        Returns:
            List of ArbitragePath objects
        """
        opportunities = []
        start_time = datetime.utcnow()
        
        # Run Bellman-Ford from each token
        for source in list(self.adjacency.keys()):
            try:
                # Get distances and predecessors
                distances, predecessors = self._bellman_ford(source)
                
                # Check for negative cycles
                if self._has_negative_cycle(distances, predecessors):
                    # Extract cycle
                    cycle_path = self._extract_cycle(predecessors, source)
                    
                    if cycle_path and len(cycle_path) <= self.max_hop_count + 1:
                        opp = self._create_opportunity(cycle_path)
                        if opp and opp.profit_percent > 0.1:  # Min 0.1% profit
                            opportunities.append(opp)
                            self.opportunities_found += 1
                            self.cycles_detected += 1
                            
            except Exception as e:
                # Continue on error
                continue
        
        self.scan_count += 1
        self.last_scan_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return opportunities
    
    def _bellman_ford(
        self,
        source: str,
    ) -> Tuple[Dict[str, float], Dict[str, Optional[Tuple[str, str]]]]:
        """
        Bellman-Ford algorithm for shortest paths
        
        Returns:
            distances: Dict[token, shortest_distance]
            predecessors: Dict[token, (previous_token, pool_address)]
        """
        # Initialize
        distances = {token: float('inf') for token in self.adjacency}
        distances[source] = 0.0
        
        predecessors = {token: None for token in self.adjacency}
        
        # Relax edges |V|-1 times
        num_iterations = len(self.adjacency) - 1
        
        for _ in range(num_iterations):
            updated = False
            
            for token in self.adjacency:
                if distances[token] == float('inf'):
                    continue
                
                for neighbor, pool_address, weight in self.adjacency[token]:
                    new_dist = distances[token] + weight
                    
                    if new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        predecessors[neighbor] = (token, pool_address)
                        updated = True
            
            # Early termination if no updates
            if not updated:
                break
        
        return distances, predecessors
    
    def _has_negative_cycle(
        self,
        distances: Dict[str, float],
        predecessors: Dict[str, Optional[Tuple[str, str]]],
    ) -> bool:
        """Check if graph has negative cycle"""
        for token in self.adjacency:
            if distances[token] == float('inf'):
                continue
            
            for neighbor, pool_address, weight in self.adjacency[token]:
                new_dist = distances[token] + weight
                
                if new_dist < distances[neighbor]:
                    return True  # Negative cycle exists
        
        return False
    
    def _extract_cycle(
        self,
        predecessors: Dict[str, Optional[Tuple[str, str]]],
        source: str,
    ) -> Optional[List[Tuple[str, str]]]:
        """
        Extract cycle path from predecessors
        
        Returns:
            List of (token, pool_address) tuples forming the cycle
        """
        # Find a node in the cycle
        cycle_node = None
        
        # Walk back |V| steps to ensure we're in the cycle
        current = source
        for _ in range(len(self.adjacency)):
            if predecessors[current] is not None:
                current = predecessors[current][0]
        
        # Now trace the cycle
        cycle_path = []
        visited = set()
        
        start_node = current
        while current not in visited:
            visited.add(current)
            cycle_path.append(current)
            
            if predecessors[current] is not None:
                current = predecessors[current][0]
            else:
                break
        
        # If we returned to start, we have a cycle
        if current == start_node and len(cycle_path) >= 2:
            # Build full path with pool addresses
            full_path = []
            for i, token in enumerate(cycle_path):
                next_token = cycle_path[(i + 1) % len(cycle_path)]
                
                # Find pool connecting these tokens
                pool_address = self._find_pool_address(token, next_token)
                if pool_address:
                    full_path.append((token, pool_address))
            
            # Add return to start
            if full_path:
                full_path.append((full_path[0][0], full_path[0][1]))
            
            return full_path
        
        return None
    
    def _find_pool_address(self, token_a: str, token_b: str) -> Optional[str]:
        """Find pool address connecting two tokens"""
        pair_key = f"{token_a}-{token_b}"
        
        if pair_key in self.pools_by_pair and self.pools_by_pair[pair_key]:
            # Return pool with best liquidity
            best_pool = max(self.pools_by_pair[pair_key], key=lambda p: p.liquidity_usd)
            return best_pool.address
        
        return None
    
    def _create_opportunity(self, cycle_path: List[Tuple[str, str]]) -> Optional[ArbitragePath]:
        """Create ArbitragePath from cycle"""
        if len(cycle_path) < 2:
            return None
        
        tokens = [token for token, _ in cycle_path[:-1]]  # Exclude duplicate end
        pools = [pool for _, pool in cycle_path[:-1]]
        
        # Get DEX names
        dexes = []
        for pool_address in pools:
            if pool_address in self.pools:
                dexes.append(self.pools[pool_address].dex)
            else:
                dexes.append("unknown")
        
        # Calculate profit using log-price weights
        total_weight = 0.0
        
        for i in range(len(cycle_path) - 1):
            token_a, pool_address = cycle_path[i]
            token_b, _ = cycle_path[i + 1]
            
            if pool_address in self.pools:
                pool = self.pools[pool_address]
                
                if token_a == pool.token_a:
                    weight = -np.log(pool.price_a_per_b) if pool.price_a_per_b > 0 else 0
                else:
                    weight = -np.log(pool.price_b_per_a) if pool.price_b_per_a > 0 else 0
                
                total_weight += weight
        
        # Profit = exp(-total_weight) - 1
        profit_percent = (np.exp(-total_weight) - 1) * 100
        
        if profit_percent <= 0:
            return None
        
        # Estimate profit in USD (assume $1000 trade)
        profit_usd = profit_percent * 10  # $1000 * profit%
        
        return ArbitragePath(
            tokens=tokens,
            pools=pools,
            dexes=dexes,
            profit_percent=profit_percent,
            profit_usd=profit_usd,
            hops=len(tokens) - 1,
        )
    
    def get_pools_for_pair(self, token_a: str, token_b: str) -> List[Pool]:
        """Get all pools for a token pair (FIXED: multi-pool support)"""
        pair_key = f"{token_a}-{token_b}"
        return self.pools_by_pair.get(pair_key, [])
    
    def get_best_pool(self, token_a: str, token_b: str) -> Optional[Pool]:
        """Get pool with best liquidity for a token pair"""
        pools = self.get_pools_for_pair(token_a, token_b)
        
        if not pools:
            return None
        
        return max(pools, key=lambda p: p.liquidity_usd)
    
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
            "nodes": len(self.tokens),
            "edges": len(self.pools),
            "token_pairs": len(self.pools_by_pair) // 2,
            "multi_pool_pairs": sum(
                1 for pools in self.pools_by_pair.values() if len(pools) > 1
            ) // 2,
            "scan_count": self.scan_count,
            "last_scan_time_ms": self.last_scan_time_ms,
            "opportunities_found": self.opportunities_found,
            "cycles_detected": self.cycles_detected,
            "avg_scan_time_ms": (
                self.last_scan_time_ms / self.scan_count if self.scan_count > 0 else 0
            ),
        }
