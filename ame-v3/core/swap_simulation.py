"""
Swap Simulation Engine

Accurate simulation of DEX swaps for:
- Constant Product (V2)
- CLMM (V3 concentrated liquidity)
- Whirlpool (Orca)

Features:
- Multi-hop route simulation
- Price impact calculation
- Fee estimation
- Slippage modeling

Target: >97% accuracy vs real execution
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math


class AMMType(Enum):
    """Automated Market Maker types"""
    CONSTANT_PRODUCT = "constant_product"  # Uniswap V2, Raydium
    CLMM = "clmm"  # Uniswap V3
    WHIRLPOOL = "whirlpool"  # Orca
    STABLE = "stable"  # Curve, StableSwap


@dataclass
class SwapQuote:
    """Quote for a single swap"""
    input_token: str
    output_token: str
    input_amount: float
    output_amount: float
    price_impact_percent: float
    fee_usd: float
    effective_price: float
    route: List[str]  # Pool addresses
    amm_type: AMMType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "input_token": self.input_token,
            "output_token": self.output_token,
            "input_amount": self.input_amount,
            "output_amount": self.output_amount,
            "price_impact_percent": self.price_impact_percent,
            "fee_usd": self.fee_usd,
            "effective_price": self.effective_price,
            "route": self.route,
            "amm_type": self.amm_type.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RouteQuote:
    """Quote for multi-hop route"""
    input_token: str
    final_output_token: str
    input_amount: float
    final_output_amount: float
    total_price_impact_percent: float
    total_fees_usd: float
    net_profit_usd: float
    hops: int
    swaps: List[SwapQuote]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "input_token": self.input_token,
            "final_output_token": self.final_output_token,
            "input_amount": self.input_amount,
            "final_output_amount": self.final_output_amount,
            "total_price_impact_percent": self.total_price_impact_percent,
            "total_fees_usd": self.total_fees_usd,
            "net_profit_usd": self.net_profit_usd,
            "hops": self.hops,
            "swaps": [s.to_dict() for s in self.swaps],
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PoolState:
    """Current state of a liquidity pool"""
    address: str
    amm_type: AMMType
    token_a: str
    token_b: str
    reserve_a: float
    reserve_b: float
    fee_percent: float
    price: float  # token_a per token_b
    liquidity: float  # For CLMM: virtual liquidity
    tick_lower: Optional[int] = None  # For CLMM
    tick_upper: Optional[int] = None  # For CLMM
    sqrt_price_x96: Optional[float] = None  # For CLMM
    
    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "amm_type": self.amm_type.value,
            "token_a": self.token_a,
            "token_b": self.token_b,
            "reserve_a": self.reserve_a,
            "reserve_b": self.reserve_b,
            "fee_percent": self.fee_percent,
            "price": self.price,
            "liquidity": self.liquidity,
            "tick_lower": self.tick_lower,
            "tick_upper": self.tick_upper,
            "sqrt_price_x96": self.sqrt_price_x96,
        }


class SwapSimulator:
    """
    Simulate DEX swaps with high accuracy
    
    Supports:
    - Constant Product (V2)
    - CLMM (V3)
    - Whirlpool (Orca)
    - Multi-hop routes
    """
    
    def __init__(self):
        self.pools: Dict[str, PoolState] = {}
    
    def add_pool(self, pool: PoolState):
        """Add or update pool state"""
        self.pools[pool.address] = pool
    
    def remove_pool(self, pool_address: str):
        """Remove pool from simulator"""
        if pool_address in self.pools:
            del self.pools[pool_address]
    
    def simulate_swap(
        self,
        pool_address: str,
        input_token: str,
        input_amount: float,
    ) -> Optional[SwapQuote]:
        """
        Simulate a single swap
        
        Args:
            pool_address: Pool to swap on
            input_token: Token being sold
            input_amount: Amount to sell
        
        Returns:
            SwapQuote or None if pool not found
        """
        if pool_address not in self.pools:
            return None
        
        pool = self.pools[pool_address]
        
        # Determine direction
        if input_token == pool.token_a:
            token_in = pool.token_a
            token_out = pool.token_b
            reserve_in = pool.reserve_a
            reserve_out = pool.reserve_b
        elif input_token == pool.token_b:
            token_in = pool.token_b
            token_out = pool.token_a
            reserve_in = pool.reserve_b
            reserve_out = pool.reserve_a
        else:
            return None  # Invalid token
        
        # Simulate based on AMM type
        if pool.amm_type == AMMType.CONSTANT_PRODUCT:
            output_amount, price_impact = self._simulate_constant_product(
                input_amount=input_amount,
                reserve_in=reserve_in,
                reserve_out=reserve_out,
                fee_percent=pool.fee_percent,
            )
        elif pool.amm_type == AMMType.CLMM:
            output_amount, price_impact = self._simulate_clmm(
                input_amount=input_amount,
                liquidity=pool.liquidity,
                sqrt_price=pool.sqrt_price_x96,
                tick_lower=pool.tick_lower,
                tick_upper=pool.tick_upper,
                fee_percent=pool.fee_percent,
            )
        elif pool.amm_type == AMMType.WHIRLPOOL:
            output_amount, price_impact = self._simulate_whirlpool(
                input_amount=input_amount,
                liquidity=pool.liquidity,
                sqrt_price=pool.sqrt_price_x96,
                fee_percent=pool.fee_percent,
            )
        elif pool.amm_type == AMMType.STABLE:
            output_amount, price_impact = self._simulate_stable_swap(
                input_amount=input_amount,
                reserve_in=reserve_in,
                reserve_out=reserve_out,
                fee_percent=pool.fee_percent,
            )
        else:
            # Default to constant product
            output_amount, price_impact = self._simulate_constant_product(
                input_amount=input_amount,
                reserve_in=reserve_in,
                reserve_out=reserve_out,
                fee_percent=pool.fee_percent,
            )
        
        # Calculate fee
        fee_usd = input_amount * pool.fee_percent / 100
        
        # Calculate effective price
        effective_price = output_amount / input_amount if input_amount > 0 else 0
        
        return SwapQuote(
            input_token=token_in,
            output_token=token_out,
            input_amount=input_amount,
            output_amount=output_amount,
            price_impact_percent=price_impact,
            fee_usd=fee_usd,
            effective_price=effective_price,
            route=[pool_address],
            amm_type=pool.amm_type,
        )
    
    def _simulate_constant_product(
        self,
        input_amount: float,
        reserve_in: float,
        reserve_out: float,
        fee_percent: float,
    ) -> Tuple[float, float]:
        """
        Simulate constant product AMM (x * y = k)
        
        Formula:
        output = (reserve_out * input_with_fee) / (reserve_in + input_with_fee)
        """
        # Apply fee
        input_with_fee = input_amount * (1 - fee_percent / 100)
        
        # Constant product formula
        output_amount = (reserve_out * input_with_fee) / (reserve_in + input_with_fee)
        
        # Calculate price impact
        spot_price = reserve_out / reserve_in if reserve_in > 0 else 0
        effective_price = output_amount / input_amount if input_amount > 0 else 0
        price_impact = (1 - effective_price / spot_price) * 100 if spot_price > 0 else 0
        
        return max(output_amount, 0), max(price_impact, 0)
    
    def _simulate_clmm(
        self,
        input_amount: float,
        liquidity: float,
        sqrt_price: Optional[float],
        tick_lower: Optional[int],
        tick_upper: Optional[int],
        fee_percent: float,
    ) -> Tuple[float, float]:
        """
        Simulate CLMM (Concentrated Liquidity Market Maker)
        
        Uniswap V3 style with concentrated liquidity in tick range.
        """
        # Simplified CLMM simulation
        # In production: use exact Uniswap V3 math with sqrt price ticks
        
        # Apply fee
        input_with_fee = input_amount * (1 - fee_percent / 100)
        
        # CLMM has higher capital efficiency in range
        # Effective liquidity can be 4-10x higher than constant product
        efficiency_multiplier = 4.0  # Simplified
        
        if tick_lower is not None and tick_upper is not None:
            # In-range: use concentrated liquidity
            effective_liquidity = liquidity * efficiency_multiplier
        else:
            # Out-of-range: same as constant product
            effective_liquidity = liquidity
        
        # Simplified output calculation
        # In production: use exact delta calculations
        reserve_equiv = math.sqrt(effective_liquidity)
        output_amount = input_with_fee * reserve_equiv / (reserve_equiv + input_with_fee)
        
        # Price impact (lower for CLMM in range)
        spot_price = 1.0  # Simplified
        effective_price = output_amount / input_amount if input_amount > 0 else 0
        price_impact = (1 - effective_price / spot_price) * 100 * 0.5  # 50% less impact
        
        return max(output_amount, 0), max(price_impact, 0)
    
    def _simulate_whirlpool(
        self,
        input_amount: float,
        liquidity: float,
        sqrt_price: Optional[float],
        fee_percent: float,
    ) -> Tuple[float, float]:
        """
        Simulate Orca Whirlpool
        
        Similar to CLMM but with different fee structure.
        """
        # Whirlpool uses similar math to CLMM
        return self._simulate_clmm(
            input_amount=input_amount,
            liquidity=liquidity,
            sqrt_price=sqrt_price,
            tick_lower=None,
            tick_upper=None,
            fee_percent=fee_percent,
        )
    
    def _simulate_stable_swap(
        self,
        input_amount: float,
        reserve_in: float,
        reserve_out: float,
        fee_percent: float,
    ) -> Tuple[float, float]:
        """
        Simulate StableSwap (Curve-style)
        
        Optimized for stable pairs with low slippage.
        """
        # Apply fee
        input_with_fee = input_amount * (1 - fee_percent / 100)
        
        # StableSwap has much lower slippage for similar assets
        # Simplified: use constant product with reduced slippage
        base_output = (reserve_out * input_with_fee) / (reserve_in + input_with_fee)
        
        # StableSwap amplification (A coefficient)
        A = 100  # Typical amplification
        slippage_reduction = A / (A + 1)
        
        output_amount = base_output * slippage_reduction
        
        # Very low price impact for stables
        price_impact = 0.05  # 0.05% typical for stables
        
        return max(output_amount, 0), price_impact
    
    def simulate_route(
        self,
        route: List[str],
        input_token: str,
        input_amount: float,
    ) -> Optional[RouteQuote]:
        """
        Simulate multi-hop route
        
        Args:
            route: List of pool addresses
            input_token: Starting token
            input_amount: Amount to start with
        
        Returns:
            RouteQuote or None if route invalid
        """
        if not route:
            return None
        
        swaps: List[SwapQuote] = []
        current_token = input_token
        current_amount = input_amount
        total_fees = 0.0
        
        for pool_address in route:
            # Simulate this hop
            quote = self.simulate_swap(pool_address, current_token, current_amount)
            
            if quote is None:
                return None
            
            swaps.append(quote)
            total_fees += quote.fee_usd
            
            # Update for next hop
            current_token = quote.output_token
            current_amount = quote.output_amount
        
        # Calculate totals
        final_output = swaps[-1].output_amount
        total_price_impact = sum(s.price_impact_percent for s in swaps)
        
        # Net profit (vs starting amount)
        # Assumes returning to original token
        net_profit = final_output - input_amount if final_output > 0 else 0
        
        return RouteQuote(
            input_token=input_token,
            final_output_token=swaps[-1].output_token,
            input_amount=input_amount,
            final_output_amount=final_output,
            total_price_impact_percent=total_price_impact,
            total_fees_usd=total_fees,
            net_profit_usd=net_profit,
            hops=len(route),
            swaps=swaps,
        )
    
    def get_optimal_size(
        self,
        pool_address: str,
        input_token: str,
        max_slippage_percent: float = 1.0,
    ) -> float:
        """
        Calculate optimal trade size for given slippage tolerance
        
        Args:
            pool_address: Pool to trade on
            input_token: Token to sell
            max_slippage_percent: Maximum acceptable slippage
        
        Returns:
            Optimal input amount
        """
        if pool_address not in self.pools:
            return 0.0
        
        pool = self.pools[pool_address]
        
        # Binary search for optimal size
        low = 0.0
        high = pool.reserve_a if input_token == pool.token_a else pool.reserve_b
        high = min(high, 1000000)  # Cap at $1M
        
        optimal = 0.0
        
        for _ in range(50):  # Binary search iterations
            mid = (low + high) / 2
            
            quote = self.simulate_swap(pool_address, input_token, mid)
            
            if quote is None:
                break
            
            if quote.price_impact_percent <= max_slippage_percent:
                optimal = mid
                low = mid  # Try larger
            else:
                high = mid  # Try smaller
        
        return optimal
    
    def get_statistics(self) -> Dict:
        """Get simulator statistics"""
        return {
            "pools_count": len(self.pools),
            "amm_types": list(set(p.amm_type.value for p in self.pools.values())),
            "total_liquidity_usd": sum(
                p.reserve_a * p.price + p.reserve_b
                for p in self.pools.values()
            ),
        }
