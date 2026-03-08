"""
Portfolio Manager

Global capital management across all strategies.

Features:
- Capital allocation optimization
- Risk constraints enforcement
- P&L tracking
- Exposure limits
- Rebalancing

Target: Maximize risk-adjusted returns
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np


@dataclass
class Position:
    """Current position in a token"""
    token: str
    amount: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl_usd: float
    realized_pnl_usd: float
    opened_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_value_usd(self) -> float:
        return self.amount * self.current_price
    
    @property
    def total_pnl_usd(self) -> float:
        return self.unrealized_pnl_usd + self.realized_pnl_usd
    
    @property
    def pnl_percent(self) -> float:
        cost_basis = self.amount * self.avg_entry_price
        if cost_basis <= 0:
            return 0.0
        return (self.total_pnl_usd / cost_basis) * 100
    
    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "amount": self.amount,
            "avg_entry_price": self.avg_entry_price,
            "current_price": self.current_price,
            "unrealized_pnl_usd": self.unrealized_pnl_usd,
            "realized_pnl_usd": self.realized_pnl_usd,
            "total_value_usd": self.total_value_usd,
            "total_pnl_usd": self.total_pnl_usd,
            "pnl_percent": self.pnl_percent,
            "opened_at": self.opened_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class PortfolioMetrics:
    """Portfolio-level metrics"""
    total_value_usd: float
    available_capital_usd: float
    allocated_capital_usd: float
    total_unrealized_pnl_usd: float
    total_realized_pnl_usd: float
    total_pnl_usd: float
    total_pnl_percent: float
    daily_pnl_usd: float
    daily_pnl_percent: float
    sharpe_ratio: float
    max_drawdown_usd: float
    max_drawdown_percent: float
    exposure_percent: float
    positions_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "total_value_usd": self.total_value_usd,
            "available_capital_usd": self.available_capital_usd,
            "allocated_capital_usd": self.allocated_capital_usd,
            "total_unrealized_pnl_usd": self.total_unrealized_pnl_usd,
            "total_realized_pnl_usd": self.total_realized_pnl_usd,
            "total_pnl_usd": self.total_pnl_usd,
            "total_pnl_percent": self.total_pnl_percent,
            "daily_pnl_usd": self.daily_pnl_usd,
            "daily_pnl_percent": self.daily_pnl_percent,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_usd": self.max_drawdown_usd,
            "max_drawdown_percent": self.max_drawdown_percent,
            "exposure_percent": self.exposure_percent,
            "positions_count": self.positions_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RiskLimits:
    """Risk limits for portfolio"""
    max_total_exposure_percent: float = 80.0  # Max % of capital deployed
    max_per_token_percent: float = 30.0  # Max % in single token
    max_per_strategy_percent: float = 40.0  # Max % to single strategy
    max_daily_loss_percent: float = 5.0  # Stop loss for day
    max_drawdown_percent: float = 10.0  # Max drawdown before stop
    max_position_size_usd: float = 50000.0  # Max single position
    max_open_positions: int = 10  # Max concurrent positions
    
    def to_dict(self) -> dict:
        return {
            "max_total_exposure_percent": self.max_total_exposure_percent,
            "max_per_token_percent": self.max_per_token_percent,
            "max_per_strategy_percent": self.max_per_strategy_percent,
            "max_daily_loss_percent": self.max_daily_loss_percent,
            "max_drawdown_percent": self.max_drawdown_percent,
            "max_position_size_usd": self.max_position_size_usd,
            "max_open_positions": self.max_open_positions,
        }


class PortfolioManager:
    """
    Manage portfolio across all strategies
    
    Responsibilities:
    - Capital allocation
    - Risk limit enforcement
    - P&L tracking
    - Rebalancing
    """
    
    def __init__(
        self,
        initial_capital_usd: float = 50000.0,
        risk_limits: RiskLimits = None,
    ):
        self.initial_capital_usd = initial_capital_usd
        self.total_capital_usd = initial_capital_usd
        
        self.risk_limits = risk_limits or RiskLimits()
        
        # Positions
        self.positions: Dict[str, Position] = {}
        
        # P&L tracking
        self.daily_start_value_usd = initial_capital_usd
        self.peak_value_usd = initial_capital_usd
        self.trough_value_usd = initial_capital_usd
        
        # Historical values for Sharpe calculation
        self.value_history: List[Tuple[datetime, float]] = []
        
        # Strategy allocations
        self.strategy_allocations: Dict[str, float] = {}
    
    def update_price(self, token: str, price: float):
        """Update token price and recalculate positions"""
        if token in self.positions:
            position = self.positions[token]
            old_value = position.total_value_usd
            
            position.current_price = price
            position.last_updated = datetime.utcnow()
            
            # Recalculate P&L
            cost_basis = position.amount * position.avg_entry_price
            new_value = position.amount * price
            position.unrealized_pnl_usd = new_value - cost_basis
            
            # Update portfolio metrics
            self._update_portfolio_metrics()
    
    def open_position(
        self,
        token: str,
        amount: float,
        entry_price: float,
        strategy_name: str,
    ) -> Tuple[bool, str]:
        """
        Open new position
        
        Args:
            token: Token to buy
            amount: Amount to buy
            entry_price: Entry price in USD
            strategy_name: Strategy that opened position
        
        Returns:
            (success, message)
        """
        # Check risk limits
        can_open, message = self._can_open_position(
            token=token,
            amount_usd=amount * entry_price,
            strategy_name=strategy_name,
        )
        
        if not can_open:
            return False, message
        
        # Calculate cost
        cost_usd = amount * entry_price
        
        # Check available capital
        if cost_usd > self.get_available_capital():
            return False, "Insufficient capital"
        
        # Open or update position
        if token in self.positions:
            # Add to existing position (average up/down)
            existing = self.positions[token]
            total_amount = existing.amount + amount
            total_cost = (existing.amount * existing.avg_entry_price) + cost_usd
            existing.avg_entry_price = total_cost / total_amount
            existing.amount = total_amount
        else:
            # New position
            self.positions[token] = Position(
                token=token,
                amount=amount,
                avg_entry_price=entry_price,
                current_price=entry_price,
                unrealized_pnl_usd=0,
                realized_pnl_usd=0,
            )
        
        # Update strategy allocation
        self.strategy_allocations[strategy_name] = (
            self.strategy_allocations.get(strategy_name, 0) + cost_usd
        )
        
        # Update portfolio metrics
        self._update_portfolio_metrics()
        
        return True, "Position opened"
    
    def close_position(
        self,
        token: str,
        amount: Optional[float] = None,
    ) -> Tuple[bool, str, float]:
        """
        Close position (fully or partially)
        
        Args:
            token: Token to sell
            amount: Amount to sell (None for full close)
        
        Returns:
            (success, message, realized_pnl_usd)
        """
        if token not in self.positions:
            return False, "Position not found", 0.0
        
        position = self.positions[token]
        
        # Determine amount to close
        if amount is None:
            amount = position.amount
        elif amount > position.amount:
            return False, "Amount exceeds position", 0.0
        
        # Calculate realized P&L
        exit_value = amount * position.current_price
        cost_basis = amount * position.avg_entry_price
        realized_pnl = exit_value - cost_basis
        
        # Update position
        position.amount -= amount
        position.realized_pnl_usd += realized_pnl
        
        if position.amount <= 0:
            # Fully closed
            del self.positions[token]
        
        # Update portfolio metrics
        self._update_portfolio_metrics()
        
        return True, "Position closed", realized_pnl
    
    def _can_open_position(
        self,
        token: str,
        amount_usd: float,
        strategy_name: str,
    ) -> Tuple[bool, str]:
        """Check if new position respects risk limits"""
        limits = self.risk_limits
        
        # Check max position size
        if amount_usd > limits.max_position_size_usd:
            return False, f"Exceeds max position size (${limits.max_position_size_usd})"
        
        # Check max open positions
        if len(self.positions) >= limits.max_open_positions:
            return False, f"Max open positions reached ({limits.max_open_positions})"
        
        # Check total exposure
        current_exposure = self.get_total_exposure()
        new_exposure = current_exposure + amount_usd
        exposure_percent = (new_exposure / self.total_capital_usd) * 100
        
        if exposure_percent > limits.max_total_exposure_percent:
            return False, f"Would exceed max exposure ({limits.max_total_exposure_percent}%)"
        
        # Check per-token limit
        if token in self.positions:
            current_token_value = self.positions[token].total_value_usd
        else:
            current_token_value = 0
        
        new_token_value = current_token_value + amount_usd
        token_percent = (new_token_value / self.total_capital_usd) * 100
        
        if token_percent > limits.max_per_token_percent:
            return False, f"Would exceed max token exposure ({limits.max_per_token_percent}%)"
        
        # Check per-strategy limit
        strategy_allocation = self.strategy_allocations.get(strategy_name, 0)
        new_strategy_allocation = strategy_allocation + amount_usd
        strategy_percent = (new_strategy_allocation / self.total_capital_usd) * 100
        
        if strategy_percent > limits.max_per_strategy_percent:
            return False, f"Would exceed max strategy allocation ({limits.max_per_strategy_percent}%)"
        
        # Check daily loss limit
        daily_pnl = self.get_daily_pnl()
        if daily_pnl < -limits.max_daily_loss_percent / 100 * self.total_capital_usd:
            return False, f"Daily loss limit reached ({limits.max_daily_loss_percent}%)"
        
        return True, "OK"
    
    def get_available_capital(self) -> float:
        """Get available (unallocated) capital"""
        allocated = sum(p.total_value_usd for p in self.positions.values())
        return self.total_capital_usd - allocated
    
    def get_total_exposure(self) -> float:
        """Get total exposure (sum of all positions)"""
        return sum(p.total_value_usd for p in self.positions.values())
    
    def get_daily_pnl(self) -> float:
        """Get daily P&L in USD"""
        current_value = sum(p.total_value_usd for p in self.positions.values())
        available = self.get_available_capital()
        return (current_value + available) - self.daily_start_value_usd
    
    def _update_portfolio_metrics(self):
        """Update portfolio-level metrics"""
        current_value = (
            sum(p.total_value_usd for p in self.positions.values()) +
            self.get_available_capital()
        )
        
        # Update peak/trough
        if current_value > self.peak_value_usd:
            self.peak_value_usd = current_value
        
        if current_value < self.trough_value_usd:
            self.trough_value_usd = current_value
        
        # Record history for Sharpe
        self.value_history.append((datetime.utcnow(), current_value))
        
        # Keep last 1000 samples
        if len(self.value_history) > 1000:
            self.value_history = self.value_history[-1000:]
    
    def get_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics"""
        current_value = (
            sum(p.total_value_usd for p in self.positions.values()) +
            self.get_available_capital()
        )
        
        total_unrealized = sum(p.unrealized_pnl_usd for p in self.positions.values())
        total_realized = sum(p.realized_pnl_usd for p in self.positions.values())
        total_pnl = total_unrealized + total_realized
        
        # Daily P&L
        daily_pnl = self.get_daily_pnl()
        daily_pnl_percent = (daily_pnl / self.daily_start_value_usd) * 100
        
        # Total P&L percent
        total_pnl_percent = (total_pnl / self.initial_capital_usd) * 100
        
        # Sharpe ratio (simplified)
        if len(self.value_history) > 10:
            values = [v for _, v in self.value_history]
            returns = np.diff(values) / values[:-1]
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        # Max drawdown
        max_drawdown = self.peak_value_usd - self.trough_value_usd
        max_drawdown_percent = (max_drawdown / self.peak_value_usd) * 100
        
        # Exposure
        exposure = self.get_total_exposure()
        exposure_percent = (exposure / self.total_capital_usd) * 100
        
        return PortfolioMetrics(
            total_value_usd=current_value,
            available_capital_usd=self.get_available_capital(),
            allocated_capital_usd=exposure,
            total_unrealized_pnl_usd=total_unrealized,
            total_realized_pnl_usd=total_realized,
            total_pnl_usd=total_pnl,
            total_pnl_percent=total_pnl_percent,
            daily_pnl_usd=daily_pnl,
            daily_pnl_percent=daily_pnl_percent,
            sharpe_ratio=sharpe,
            max_drawdown_usd=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            exposure_percent=exposure_percent,
            positions_count=len(self.positions),
        )
    
    def rebalance(self) -> List[str]:
        """
        Rebalance portfolio to respect limits
        
        Returns:
            List of actions taken
        """
        actions = []
        limits = self.risk_limits
        
        # Check each position
        for token, position in list(self.positions.items()):
            value = position.total_value_usd
            percent = (value / self.total_capital_usd) * 100
            
            # Reduce if over limit
            if percent > limits.max_per_token_percent:
                # Calculate amount to sell
                excess_percent = percent - limits.max_per_token_percent
                excess_amount = position.amount * (excess_percent / percent)
                
                # Close partial position
                success, msg, pnl = self.close_position(token, excess_amount)
                if success:
                    actions.append(f"Reduced {token} by {excess_amount:.4f}")
        
        return actions
    
    def reset_daily_pnl(self):
        """Reset daily P&L tracking (call at start of trading day)"""
        self.daily_start_value_usd = (
            sum(p.total_value_usd for p in self.positions.values()) +
            self.get_available_capital()
        )
        self.peak_value_usd = self.daily_start_value_usd
        self.trough_value_usd = self.daily_start_value_usd
    
    def get_statistics(self) -> Dict:
        """Get portfolio manager statistics"""
        metrics = self.get_metrics()
        return {
            "initial_capital_usd": self.initial_capital_usd,
            "total_capital_usd": self.total_capital_usd,
            "metrics": metrics.to_dict(),
            "risk_limits": self.risk_limits.to_dict(),
            "strategies": list(self.strategy_allocations.keys()),
        }
