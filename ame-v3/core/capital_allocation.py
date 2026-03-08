"""
Capital Allocation Engine

Optimal trade size optimization using:
- Newton-Raphson method
- Liquidity curves
- Risk constraints

Target: Maximize profit while respecting capital limits
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from scipy.optimize import minimize_scalar, minimize


@dataclass
class AllocationResult:
    """Result of capital allocation optimization"""
    opportunity_id: str
    optimal_size_usd: float
    expected_profit_usd: float
    roi_percent: float
    confidence: float
    risk_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "optimal_size_usd": self.optimal_size_usd,
            "expected_profit_usd": self.expected_profit_usd,
            "roi_percent": self.roi_percent,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PortfolioAllocation:
    """Full portfolio allocation across multiple opportunities"""
    allocations: List[AllocationResult]
    total_capital_allocated: float
    total_expected_profit: float
    total_roi_percent: float
    remaining_capital: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "allocations": [a.to_dict() for a in self.allocations],
            "total_capital_allocated": self.total_capital_allocated,
            "total_expected_profit": self.total_expected_profit,
            "total_roi_percent": self.total_roi_percent,
            "remaining_capital": self.remaining_capital,
            "timestamp": self.timestamp.isoformat(),
        }


class LiquidityCurve:
    """
    Model liquidity curves for slippage calculation
    
    Supports:
    - Constant product (V2)
    - CLMM (V3 concentrated liquidity)
    - Whirlpool (Orca)
    """
    
    def __init__(self, amm_type: str = "constant_product"):
        self.amm_type = amm_type
        self.liquidity = 0.0
        self.price = 0.0
        self.tick_range = None
    
    def set_parameters(
        self,
        liquidity: float,
        price: float,
        tick_range: Tuple[float, float] = None,
    ):
        """Set curve parameters"""
        self.liquidity = liquidity
        self.price = price
        self.tick_range = tick_range
    
    def get_output_amount(
        self,
        input_amount: float,
        input_token: str,
    ) -> float:
        """
        Calculate output amount for given input
        
        Args:
            input_amount: Amount of input token
            input_token: Input token address
        
        Returns:
            Output amount after slippage
        """
        if self.amm_type == "constant_product":
            return self._simulate_constant_product(input_amount)
        elif self.amm_type == "clmm":
            return self._simulate_clmm(input_amount)
        elif self.amm_type == "whirlpool":
            return self._simulate_whirlpool(input_amount)
        else:
            return self._simulate_constant_product(input_amount)
    
    def _simulate_constant_product(self, input_amount: float) -> float:
        """Constant product AMM (x * y = k)"""
        # Simplified: output = input * price * (1 - slippage)
        # Slippage increases with trade size relative to liquidity
        slippage = (input_amount / self.liquidity) * 0.5  # 0.5 coefficient
        output = input_amount * self.price * (1 - slippage)
        return max(output, 0)
    
    def _simulate_clmm(self, input_amount: float) -> float:
        """Concentrated Liquidity Market Maker (V3)"""
        # CLMM has better capital efficiency in range
        if self.tick_range:
            # In-range: lower slippage
            efficiency = 4.0  # CLMM can be 4x more efficient
            effective_liquidity = self.liquidity * efficiency
        else:
            # Out-of-range: same as constant product
            effective_liquidity = self.liquidity
        
        slippage = (input_amount / effective_liquidity) * 0.5
        output = input_amount * self.price * (1 - slippage)
        return max(output, 0)
    
    def _simulate_whirlpool(self, input_amount: float) -> float:
        """Orca Whirlpool (similar to CLMM)"""
        return self._simulate_clmm(input_amount)
    
    def get_price_impact(self, input_amount: float) -> float:
        """Calculate price impact percentage"""
        if self.liquidity <= 0:
            return 100.0
        
        base_output = input_amount * self.price
        actual_output = self.get_output_amount(input_amount, "")
        
        if base_output <= 0:
            return 100.0
        
        impact = (base_output - actual_output) / base_output * 100
        return impact


class CapitalAllocationEngine:
    """
    Optimize capital allocation across opportunities
    
    Methods:
    - Newton-Raphson for single opportunity
    - Grid search for multi-opportunity
    - Risk-adjusted optimization
    """
    
    def __init__(
        self,
        total_capital_usd: float = 50000.0,
        max_per_opp_percent: float = 20.0,
        max_per_token_percent: float = 30.0,
        min_trade_size_usd: float = 1000.0,
    ):
        self.total_capital_usd = total_capital_usd
        self.max_per_opp_percent = max_per_opp_percent
        self.max_per_token_percent = max_per_token_percent
        self.min_trade_size_usd = min_trade_size_usd
        
        # Liquidity curves for each pool
        self.liquidity_curves: Dict[str, LiquidityCurve] = {}
    
    def set_liquidity_curve(
        self,
        pool_address: str,
        curve: LiquidityCurve,
    ):
        """Set liquidity curve for a pool"""
        self.liquidity_curves[pool_address] = curve
    
    def optimize_single_opportunity(
        self,
        opportunity_id: str,
        profit_function: callable,
        min_size: float = None,
        max_size: float = None,
    ) -> Optional[AllocationResult]:
        """
        Optimize trade size for single opportunity using Newton-Raphson
        
        Args:
            opportunity_id: Unique identifier
            profit_function: Function(size) -> profit
            min_size: Minimum trade size
            max_size: Maximum trade size
        
        Returns:
            AllocationResult with optimal size
        """
        if min_size is None:
            min_size = self.min_trade_size_usd
        
        if max_size is None:
            max_size = self.total_capital_usd * self.max_per_opp_percent / 100
        
        # Use scipy to maximize profit
        def neg_profit(size):
            return -profit_function(size)
        
        result = minimize_scalar(
            neg_profit,
            bounds=(min_size, max_size),
            method='bounded',
        )
        
        if not result.success:
            return None
        
        optimal_size = result.x
        expected_profit = -result.fun
        
        if expected_profit <= 0:
            return None
        
        roi = (expected_profit / optimal_size) * 100
        
        return AllocationResult(
            opportunity_id=opportunity_id,
            optimal_size_usd=optimal_size,
            expected_profit_usd=expected_profit,
            roi_percent=roi,
            confidence=0.85,
            risk_score=0.2,
        )
    
    def optimize_portfolio(
        self,
        opportunities: List[Dict],
    ) -> PortfolioAllocation:
        """
        Optimize allocation across multiple opportunities
        
        Args:
            opportunities: List of opportunity dicts with:
                - id: str
                - profit_function: callable
                - token: str (for concentration limits)
        
        Returns:
            PortfolioAllocation
        """
        if not opportunities:
            return self._empty_allocation()
        
        # Greedy optimization by ROI
        # (Production: use quadratic programming for true optimization)
        
        allocations = []
        remaining_capital = self.total_capital_usd
        token_exposure: Dict[str, float] = {}
        
        # Sort by expected ROI (simplified - use profit_function(1000))
        def estimate_roi(opp):
            try:
                profit = opp["profit_function"](1000)
                return profit / 1000 if profit > 0 else 0
            except:
                return 0
        
        sorted_opps = sorted(opportunities, key=estimate_roi, reverse=True)
        
        for opp in sorted_opps:
            if remaining_capital < self.min_trade_size_usd:
                break
            
            opp_id = opp.get("id", "unknown")
            token = opp.get("token", "unknown")
            profit_fn = opp.get("profit_function", lambda x: x * 0.001)
            
            # Check token concentration limit
            current_exposure = token_exposure.get(token, 0)
            max_exposure = self.total_capital_usd * self.max_per_token_percent / 100
            
            if current_exposure >= max_exposure:
                continue  # Skip, already at limit
            
            # Optimize this opportunity
            max_size = min(
                remaining_capital,
                self.total_capital_usd * self.max_per_opp_percent / 100,
                max_exposure - current_exposure,
            )
            
            result = self.optimize_single_opportunity(
                opportunity_id=opp_id,
                profit_function=profit_fn,
                min_size=self.min_trade_size_usd,
                max_size=max_size,
            )
            
            if result:
                allocations.append(result)
                remaining_capital -= result.optimal_size_usd
                token_exposure[token] = token_exposure.get(token, 0) + result.optimal_size_usd
        
        # Calculate totals
        total_allocated = sum(a.optimal_size_usd for a in allocations)
        total_profit = sum(a.expected_profit_usd for a in allocations)
        total_roi = (total_profit / total_allocated * 100) if total_allocated > 0 else 0
        
        return PortfolioAllocation(
            allocations=allocations,
            total_capital_allocated=total_allocated,
            total_expected_profit=total_profit,
            total_roi_percent=total_roi,
            remaining_capital=remaining_capital,
        )
    
    def _empty_allocation(self) -> PortfolioAllocation:
        """Return empty allocation"""
        return PortfolioAllocation(
            allocations=[],
            total_capital_allocated=0,
            total_expected_profit=0,
            total_roi_percent=0,
            remaining_capital=self.total_capital_usd,
        )
    
    def calculate_slippage(
        self,
        pool_address: str,
        amount_usd: float,
    ) -> float:
        """Calculate expected slippage for a trade"""
        if pool_address not in self.liquidity_curves:
            return 1.0  # Default 1% slippage
        
        curve = self.liquidity_curves[pool_address]
        return curve.get_price_impact(amount_usd)
    
    def get_statistics(self) -> Dict:
        """Get allocation engine statistics"""
        return {
            "total_capital_usd": self.total_capital_usd,
            "max_per_opp_percent": self.max_per_opp_percent,
            "max_per_token_percent": self.max_per_token_percent,
            "min_trade_size_usd": self.min_trade_size_usd,
            "liquidity_curves_count": len(self.liquidity_curves),
        }
