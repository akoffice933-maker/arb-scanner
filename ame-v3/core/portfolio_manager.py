"""
Portfolio Manager v2 — Fixed Cash + Positions Model

Proper accounting:
- Cash ledger (real balance tracking)
- Positions with cost basis
- Realized PnL (returned to cash on close)
- Unrealized PnL (mark-to-market)
- Accurate daily PnL calculation

Target: Production-grade accounting
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np


class PositionStatus(Enum):
    """Position lifecycle status"""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


@dataclass
class Position:
    """Position with proper cost basis tracking"""
    token: str
    amount: float
    avg_entry_price: float
    current_price: float
    status: PositionStatus = PositionStatus.OPEN
    opened_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def cost_basis_usd(self) -> float:
        """Original cost basis"""
        return self.amount * self.avg_entry_price
    
    @property
    def market_value_usd(self) -> float:
        """Current market value"""
        return self.amount * self.current_price
    
    @property
    def unrealized_pnl_usd(self) -> float:
        """Unrealized PnL (mark-to-market)"""
        return self.market_value_usd - self.cost_basis_usd
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """Unrealized PnL percentage"""
        if self.cost_basis_usd <= 0:
            return 0.0
        return (self.unrealized_pnl_usd / self.cost_basis_usd) * 100
    
    def update_price(self, price: float):
        """Update current price"""
        self.current_price = price
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "amount": self.amount,
            "avg_entry_price": self.avg_entry_price,
            "current_price": self.current_price,
            "cost_basis_usd": self.cost_basis_usd,
            "market_value_usd": self.market_value_usd,
            "unrealized_pnl_usd": self.unrealized_pnl_usd,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class CashLedger:
    """Cash balance tracking with transaction history"""
    initial_balance_usd: float
    available_balance_usd: float
    realized_pnl_usd: float = 0.0
    total_fees_paid_usd: float = 0.0
    total_gas_paid_usd: float = 0.0
    
    # Transaction history
    transactions: List[Dict] = field(default_factory=list)
    
    def record_transaction(
        self,
        tx_type: str,
        amount_usd: float,
        description: str,
        balance_after: float,
    ):
        """Record a transaction in the ledger"""
        self.transactions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": tx_type,
            "amount_usd": amount_usd,
            "description": description,
            "balance_after": balance_after,
        })
        
        # Keep last 1000 transactions
        if len(self.transactions) > 1000:
            self.transactions = self.transactions[-1000:]
    
    def deposit(self, amount_usd: float, description: str = "Deposit"):
        """Add funds to cash ledger"""
        self.available_balance_usd += amount_usd
        self.record_transaction("deposit", amount_usd, description, self.available_balance_usd)
    
    def withdraw(self, amount_usd: float, description: str = "Withdrawal") -> Tuple[bool, str]:
        """Remove funds from cash ledger"""
        if amount_usd > self.available_balance_usd:
            return False, "Insufficient cash balance"
        
        self.available_balance_usd -= amount_usd
        self.record_transaction("withdrawal", -amount_usd, description, self.available_balance_usd)
        return True, "OK"
    
    def add_realized_pnl(self, pnl_usd: float):
        """Add realized PnL to cash balance"""
        self.available_balance_usd += pnl_usd
        self.realized_pnl_usd += pnl_usd
        
        pnl_type = "profit" if pnl_usd > 0 else "loss"
        self.record_transaction(
            "realized_pnl",
            pnl_usd,
            f"Realized {pnl_type} from position close",
            self.available_balance_usd,
        )
    
    def deduct_fees(self, fees_usd: float, gas_usd: float = 0.0):
        """Deduct fees and gas from cash balance"""
        total = fees_usd + gas_usd
        
        if total > self.available_balance_usd:
            # Allow negative balance for fees (should be rare)
            pass
        
        self.available_balance_usd -= total
        self.total_fees_paid_usd += fees_usd
        self.total_gas_paid_usd += gas_usd
        
        self.record_transaction(
            "fee",
            -total,
            f"Trading fees (${fees_usd:.2f}) + gas (${gas_usd:.2f})",
            self.available_balance_usd,
        )
    
    def get_total_equity(self, positions_value_usd: float) -> float:
        """Get total equity (cash + positions)"""
        return self.available_balance_usd + positions_value_usd
    
    def get_daily_pnl(
        self,
        positions_value_usd: float,
        daily_start_equity_usd: float,
    ) -> float:
        """Calculate daily PnL based on total equity"""
        current_equity = self.get_total_equity(positions_value_usd)
        return current_equity - daily_start_equity_usd
    
    def to_dict(self) -> dict:
        return {
            "initial_balance_usd": self.initial_balance_usd,
            "available_balance_usd": self.available_balance_usd,
            "realized_pnl_usd": self.realized_pnl_usd,
            "total_fees_paid_usd": self.total_fees_paid_usd,
            "total_gas_paid_usd": self.total_gas_paid_usd,
            "transaction_count": len(self.transactions),
        }


@dataclass
class RiskLimits:
    """Risk limits for portfolio"""
    max_total_exposure_percent: float = 80.0
    max_per_token_percent: float = 30.0
    max_per_strategy_percent: float = 40.0
    max_daily_loss_percent: float = 5.0  # Only triggers on LOSS
    max_drawdown_percent: float = 10.0
    max_position_size_usd: float = 50000.0
    max_open_positions: int = 10
    
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


@dataclass
class PortfolioMetrics:
    """Portfolio-level metrics"""
    total_equity_usd: float
    cash_balance_usd: float
    positions_value_usd: float
    total_unrealized_pnl_usd: float
    total_realized_pnl_usd: float
    daily_pnl_usd: float
    daily_pnl_percent: float
    total_pnl_usd: float
    total_pnl_percent: float
    sharpe_ratio: float
    max_drawdown_usd: float
    max_drawdown_percent: float
    exposure_percent: float
    positions_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "total_equity_usd": self.total_equity_usd,
            "cash_balance_usd": self.cash_balance_usd,
            "positions_value_usd": self.positions_value_usd,
            "total_unrealized_pnl_usd": self.total_unrealized_pnl_usd,
            "total_realized_pnl_usd": self.total_realized_pnl_usd,
            "daily_pnl_usd": self.daily_pnl_usd,
            "daily_pnl_percent": self.daily_pnl_percent,
            "total_pnl_usd": self.total_pnl_usd,
            "total_pnl_percent": self.total_pnl_percent,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_usd": self.max_drawdown_usd,
            "max_drawdown_percent": self.max_drawdown_percent,
            "exposure_percent": self.exposure_percent,
            "positions_count": self.positions_count,
            "timestamp": self.timestamp.isoformat(),
        }


class PortfolioManager:
    """
    Portfolio Manager v2 — Fixed Accounting Model
    
    Key fixes:
    - Proper cash ledger tracking
    - Realized PnL returned to cash on close
    - Daily PnL based on total equity (cash + positions)
    - Kill-switch only triggers on actual losses
    """
    
    def __init__(
        self,
        initial_capital_usd: float = 50000.0,
        risk_limits: RiskLimits = None,
    ):
        self.initial_capital_usd = initial_capital_usd
        
        # Cash ledger (FIXED: proper tracking)
        self.cash = CashLedger(
            initial_balance_usd=initial_capital_usd,
            available_balance_usd=initial_capital_usd,
        )
        
        # Positions
        self.positions: Dict[str, Position] = {}
        
        # Risk limits
        self.risk_limits = risk_limits or RiskLimits()
        
        # Daily tracking (FIXED: based on total equity)
        self.daily_start_equity_usd = initial_capital_usd
        self.peak_equity_usd = initial_capital_usd
        self.trough_equity_usd = initial_capital_usd
        
        # Historical equity for Sharpe calculation
        self.equity_history: List[Tuple[datetime, float]] = []
        
        # Strategy allocations
        self.strategy_allocations: Dict[str, float] = {}
    
    def update_price(self, token: str, price: float):
        """Update token price and recalculate positions"""
        if token in self.positions:
            position = self.positions[token]
            position.update_price(price)
    
    def open_position(
        self,
        token: str,
        amount: float,
        entry_price: float,
        strategy_name: str,
        fees_usd: float = 0.0,
        gas_usd: float = 0.0,
    ) -> Tuple[bool, str]:
        """
        Open new position (FIXED: proper cash deduction)
        
        Args:
            token: Token to buy
            amount: Amount to buy
            entry_price: Entry price in USD
            strategy_name: Strategy that opened position
            fees_usd: Trading fees
            gas_usd: Gas costs
        
        Returns:
            (success, message)
        """
        # Calculate total cost
        cost_usd = amount * entry_price + fees_usd + gas_usd
        
        # Check available cash (FIXED: use cash ledger)
        if cost_usd > self.cash.available_balance_usd:
            return False, "Insufficient cash balance"
        
        # Check risk limits
        can_open, message = self._can_open_position(
            token=token,
            amount_usd=amount * entry_price,
            strategy_name=strategy_name,
        )
        
        if not can_open:
            return False, message
        
        # Deduct cash (FIXED: proper accounting)
        self.cash.available_balance_usd -= cost_usd
        if fees_usd > 0 or gas_usd > 0:
            self.cash.deduct_fees(fees_usd, gas_usd)
        
        # Open or update position
        if token in self.positions:
            # Add to existing position (average up/down)
            existing = self.positions[token]
            total_cost = existing.cost_basis_usd + (amount * entry_price)
            total_amount = existing.amount + amount
            existing.avg_entry_price = total_cost / total_amount if total_amount > 0 else entry_price
            existing.amount = total_amount
        else:
            # New position
            self.positions[token] = Position(
                token=token,
                amount=amount,
                avg_entry_price=entry_price,
                current_price=entry_price,
            )
        
        # Update strategy allocation
        self.strategy_allocations[strategy_name] = (
            self.strategy_allocations.get(strategy_name, 0) + (amount * entry_price)
        )
        
        return True, "Position opened"
    
    def close_position(
        self,
        token: str,
        exit_price: float,
        amount: Optional[float] = None,
        fees_usd: float = 0.0,
        gas_usd: float = 0.0,
    ) -> Tuple[bool, str, float]:
        """
        Close position (FIXED: realized PnL returned to cash)
        
        Args:
            token: Token to sell
            exit_price: Exit price in USD
            amount: Amount to sell (None for full close)
            fees_usd: Trading fees
            gas_usd: Gas costs
        
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
        
        # Calculate proceeds and PnL (FIXED: proper accounting)
        proceeds_usd = amount * exit_price
        cost_basis_usd = amount * position.avg_entry_price
        realized_pnl = proceeds_usd - cost_basis_usd - fees_usd - gas_usd
        
        # Add proceeds to cash (FIXED: realized PnL properly tracked)
        self.cash.available_balance_usd += proceeds_usd
        
        # Deduct fees
        if fees_usd > 0 or gas_usd > 0:
            self.cash.deduct_fees(fees_usd, gas_usd)
        
        # Record realized PnL in ledger (FIXED)
        self.cash.add_realized_pnl(realized_pnl)
        
        # Update position
        position.amount -= amount
        
        if position.amount <= 0:
            # Fully closed
            position.status = PositionStatus.CLOSED
            del self.positions[token]
        else:
            # Partially closed — update cost basis
            position.avg_entry_price = position.cost_basis_usd / position.amount
        
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
        
        # Check total exposure (FIXED: use positions value)
        current_exposure = sum(p.market_value_usd for p in self.positions.values())
        new_exposure = current_exposure + amount_usd
        total_equity = self.cash.get_total_equity(current_exposure)
        exposure_percent = (new_exposure / total_equity) * 100 if total_equity > 0 else 100
        
        if exposure_percent > limits.max_total_exposure_percent:
            return False, f"Would exceed max exposure ({limits.max_total_exposure_percent}%)"
        
        # Check per-token limit
        if token in self.positions:
            current_token_value = self.positions[token].market_value_usd
        else:
            current_token_value = 0
        
        new_token_value = current_token_value + amount_usd
        token_percent = (new_token_value / total_equity) * 100 if total_equity > 0 else 100
        
        if token_percent > limits.max_per_token_percent:
            return False, f"Would exceed max token exposure ({limits.max_per_token_percent}%)"
        
        # Check per-strategy limit
        strategy_allocation = self.strategy_allocations.get(strategy_name, 0)
        new_strategy_allocation = strategy_allocation + amount_usd
        strategy_percent = (new_strategy_allocation / total_equity) * 100 if total_equity > 0 else 100
        
        if strategy_percent > limits.max_per_strategy_percent:
            return False, f"Would exceed max strategy allocation ({limits.max_per_strategy_percent}%)"
        
        # Check daily loss limit (FIXED: only on actual loss)
        daily_pnl = self.get_daily_pnl()
        if daily_pnl < -(limits.max_daily_loss_percent / 100 * self.daily_start_equity_usd):
            return False, f"Daily loss limit reached ({limits.max_daily_loss_percent}%)"
        
        return True, "OK"
    
    def get_available_capital(self) -> float:
        """Get available cash (FIXED: from cash ledger)"""
        return self.cash.available_balance_usd
    
    def get_total_exposure(self) -> float:
        """Get total exposure (sum of all positions)"""
        return sum(p.market_value_usd for p in self.positions.values())
    
    def get_daily_pnl(self) -> float:
        """
        Get daily PnL in USD (FIXED: based on total equity)
        
        Formula: (cash + positions) - daily_start_equity
        """
        positions_value = self.get_total_exposure()
        return self.cash.get_daily_pnl(positions_value, self.daily_start_equity_usd)
    
    def _update_portfolio_metrics(self):
        """Update portfolio-level metrics"""
        positions_value = self.get_total_exposure()
        current_equity = self.cash.get_total_equity(positions_value)
        
        # Update peak/trough equity
        if current_equity > self.peak_equity_usd:
            self.peak_equity_usd = current_equity
        
        if current_equity < self.trough_equity_usd:
            self.trough_equity_usd = current_equity
        
        # Record history for Sharpe
        self.equity_history.append((datetime.utcnow(), current_equity))
        
        # Keep last 1000 samples
        if len(self.equity_history) > 1000:
            self.equity_history = self.equity_history[-1000:]
    
    def get_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics (FIXED)"""
        positions_value = self.get_total_exposure()
        total_equity = self.cash.get_total_equity(positions_value)
        
        # PnL calculations (FIXED)
        total_unrealized = sum(p.unrealized_pnl_usd for p in self.positions.values())
        total_realized = self.cash.realized_pnl_usd
        total_pnl = total_unrealized + total_realized
        
        # Daily PnL (FIXED: based on equity)
        daily_pnl = self.get_daily_pnl()
        daily_pnl_percent = (daily_pnl / self.daily_start_equity_usd) * 100 if self.daily_start_equity_usd > 0 else 0
        
        # Total PnL percent
        total_pnl_percent = (total_pnl / self.initial_capital_usd) * 100
        
        # Sharpe ratio
        if len(self.equity_history) > 10:
            values = [v for _, v in self.equity_history]
            returns = np.diff(values) / values[:-1]
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        # Max drawdown (FIXED: based on equity)
        max_drawdown = self.peak_equity_usd - self.trough_equity_usd
        max_drawdown_percent = (max_drawdown / self.peak_equity_usd) * 100 if self.peak_equity_usd > 0 else 0
        
        # Exposure
        exposure = self.get_total_exposure()
        exposure_percent = (exposure / total_equity) * 100 if total_equity > 0 else 0
        
        return PortfolioMetrics(
            total_equity_usd=total_equity,
            cash_balance_usd=self.cash.available_balance_usd,
            positions_value_usd=positions_value,
            total_unrealized_pnl_usd=total_unrealized,
            total_realized_pnl_usd=total_realized,
            daily_pnl_usd=daily_pnl,
            daily_pnl_percent=daily_pnl_percent,
            total_pnl_usd=total_pnl,
            total_pnl_percent=total_pnl_percent,
            sharpe_ratio=sharpe,
            max_drawdown_usd=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            exposure_percent=exposure_percent,
            positions_count=len(self.positions),
        )
    
    def rebalance(self) -> List[str]:
        """Rebalance portfolio to respect limits"""
        actions = []
        limits = self.risk_limits
        total_equity = self.cash.get_total_equity(self.get_total_exposure())
        
        # Check each position
        for token, position in list(self.positions.items()):
            value = position.market_value_usd
            percent = (value / total_equity) * 100 if total_equity > 0 else 0
            
            # Reduce if over limit
            if percent > limits.max_per_token_percent:
                excess_percent = percent - limits.max_per_token_percent
                excess_amount = position.amount * (excess_percent / percent) if percent > 0 else 0
                
                # In production: would trigger market order
                actions.append(f"Would reduce {token} by {excess_amount:.4f} ({excess_percent:.1f}% over limit)")
        
        return actions
    
    def reset_daily_pnl(self):
        """Reset daily PnL tracking (call at start of trading day)"""
        positions_value = self.get_total_exposure()
        self.daily_start_equity_usd = self.cash.get_total_equity(positions_value)
        self.peak_equity_usd = self.daily_start_equity_usd
        self.trough_equity_usd = self.daily_start_equity_usd
    
    def get_statistics(self) -> Dict:
        """Get portfolio manager statistics"""
        metrics = self.get_metrics()
        return {
            "initial_capital_usd": self.initial_capital_usd,
            "cash_ledger": self.cash.to_dict(),
            "metrics": metrics.to_dict(),
            "risk_limits": self.risk_limits.to_dict(),
            "strategies": list(self.strategy_allocations.keys()),
        }
