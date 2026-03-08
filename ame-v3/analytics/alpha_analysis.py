"""
Historical Alpha Analysis

Analyze historical performance to identify:
- Profit distribution
- Win rate
- Average edge
- Sharpe ratio
- Max drawdown
- Strategy performance
- Alpha decay time

Target: Data-driven strategy optimization
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from scipy import stats


@dataclass
class PerformanceMetrics:
    """Historical performance metrics"""
    total_opportunities: int
    executed_count: int
    win_count: int
    loss_count: int
    win_rate: float
    total_profit_usd: float
    avg_profit_usd: float
    median_profit_usd: float
    std_profit_usd: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_usd: float
    max_drawdown_percent: float
    avg_edge_percent: float
    alpha_decay_time_ms: float
    period_days: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "total_opportunities": self.total_opportunities,
            "executed_count": self.executed_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self.win_rate,
            "total_profit_usd": self.total_profit_usd,
            "avg_profit_usd": self.avg_profit_usd,
            "median_profit_usd": self.median_profit_usd,
            "std_profit_usd": self.std_profit_usd,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown_usd": self.max_drawdown_usd,
            "max_drawdown_percent": self.max_drawdown_percent,
            "avg_edge_percent": self.avg_edge_percent,
            "alpha_decay_time_ms": self.alpha_decay_time_ms,
            "period_days": self.period_days,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StrategyPerformance:
    """Performance metrics for a single strategy"""
    strategy_name: str
    opportunities_count: int
    win_rate: float
    total_profit_usd: float
    avg_profit_usd: float
    sharpe_ratio: float
    avg_holding_time_ms: float
    best_trade_usd: float
    worst_trade_usd: float
    consecutive_wins: int
    consecutive_losses: int
    
    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "opportunities_count": self.opportunities_count,
            "win_rate": self.win_rate,
            "total_profit_usd": self.total_profit_usd,
            "avg_profit_usd": self.avg_profit_usd,
            "sharpe_ratio": self.sharpe_ratio,
            "avg_holding_time_ms": self.avg_holding_time_ms,
            "best_trade_usd": self.best_trade_usd,
            "worst_trade_usd": self.worst_trade_usd,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
        }


@dataclass
class Trade:
    """Historical trade record"""
    id: str
    strategy_name: str
    timestamp: datetime
    entry_time: datetime
    exit_time: Optional[datetime]
    profit_usd: float
    profit_percent: float
    size_usd: float
    success: bool
    fees_usd: float
    gas_usd: float
    tip_usd: float
    slippage_percent: float
    
    def holding_time_ms(self) -> float:
        """Calculate holding time in milliseconds"""
        if self.exit_time is None:
            return 0.0
        return (self.exit_time - self.entry_time).total_seconds() * 1000


class HistoricalAlphaAnalyzer:
    """
    Analyze historical alpha and performance
    
    Metrics:
    - Profit distribution
    - Win rate
    - Sharpe/Sortino ratios
    - Max drawdown
    - Alpha decay
    - Strategy comparison
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        self.trades: List[Trade] = []
        self.opportunities_seen = 0
    
    def add_trade(self, trade: Trade):
        """Add trade to history"""
        self.trades.append(trade)
        
        # Keep last 10000 trades
        if len(self.trades) > 10000:
            self.trades = self.trades[-10000:]
    
    def record_opportunity(self, seen: bool = True):
        """Record opportunity (seen or missed)"""
        if seen:
            self.opportunities_seen += 1
    
    def calculate_performance_metrics(
        self,
        days: int = 30,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics
        
        Args:
            days: Lookback period in days
        
        Returns:
            PerformanceMetrics
        """
        # Filter trades by period
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_trades = [t for t in self.trades if t.timestamp >= cutoff]
        
        if not recent_trades:
            return self._empty_metrics(days)
        
        # Basic counts
        win_count = sum(1 for t in recent_trades if t.success)
        loss_count = len(recent_trades) - win_count
        win_rate = win_count / len(recent_trades) * 100 if recent_trades else 0
        
        # Profit statistics
        profits = [t.profit_usd for t in recent_trades]
        total_profit = sum(profits)
        avg_profit = np.mean(profits)
        median_profit = np.median(profits)
        std_profit = np.std(profits)
        
        # Risk-adjusted returns
        if std_profit > 0:
            sharpe_ratio = (avg_profit - self.risk_free_rate / 252) / std_profit * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Sortino ratio (downside deviation)
        downside_profits = [p for p in profits if p < 0]
        if downside_profits:
            downside_std = np.std(downside_profits)
            sortino_ratio = (avg_profit - self.risk_free_rate / 252) / downside_std * np.sqrt(252)
        else:
            sortino_ratio = float('inf') if avg_profit > 0 else 0
        
        # Max drawdown
        cumulative = np.cumsum(profits)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_drawdown = np.max(drawdown)
        max_drawdown_percent = (max_drawdown / np.max(peak) * 100) if np.max(peak) > 0 else 0
        
        # Average edge
        avg_edge = np.mean([t.profit_percent for t in recent_trades])
        
        # Alpha decay time
        alpha_decay = self._calculate_alpha_decay(recent_trades)
        
        return PerformanceMetrics(
            total_opportunities=self.opportunities_seen,
            executed_count=len(recent_trades),
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            total_profit_usd=total_profit,
            avg_profit_usd=avg_profit,
            median_profit_usd=median_profit,
            std_profit_usd=std_profit,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown_usd=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            avg_edge_percent=avg_edge,
            alpha_decay_time_ms=alpha_decay,
            period_days=days,
        )
    
    def _calculate_alpha_decay(self, trades: List[Trade]) -> float:
        """
        Calculate alpha decay time
        
        Alpha decay = time until profit opportunity disappears
        
        Method:
        1. Group opportunities by timestamp
        2. Measure how long similar opportunities remain profitable
        """
        if len(trades) < 10:
            return 5000.0  # Default 5 seconds
        
        # Simplified: use average holding time as proxy
        holding_times = [t.holding_time_ms() for t in trades if t.exit_time]
        
        if not holding_times:
            return 5000.0
        
        return np.median(holding_times)
    
    def _empty_metrics(self, days: int) -> PerformanceMetrics:
        """Return empty metrics"""
        return PerformanceMetrics(
            total_opportunities=0,
            executed_count=0,
            win_count=0,
            loss_count=0,
            win_rate=0,
            total_profit_usd=0,
            avg_profit_usd=0,
            median_profit_usd=0,
            std_profit_usd=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            max_drawdown_usd=0,
            max_drawdown_percent=0,
            avg_edge_percent=0,
            alpha_decay_time_ms=0,
            period_days=days,
        )
    
    def analyze_strategy_performance(
        self,
        strategy_name: str,
        days: int = 30,
    ) -> Optional[StrategyPerformance]:
        """
        Analyze performance for a specific strategy
        
        Args:
            strategy_name: Strategy to analyze
            days: Lookback period
        
        Returns:
            StrategyPerformance or None
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        strategy_trades = [
            t for t in self.trades
            if t.strategy_name == strategy_name and t.timestamp >= cutoff
        ]
        
        if not strategy_trades:
            return None
        
        # Win rate
        wins = [t for t in strategy_trades if t.success]
        win_rate = len(wins) / len(strategy_trades) * 100
        
        # Profits
        profits = [t.profit_usd for t in strategy_trades]
        total_profit = sum(profits)
        avg_profit = np.mean(profits)
        
        # Sharpe ratio
        if np.std(profits) > 0:
            sharpe = (avg_profit - self.risk_free_rate / 252) / np.std(profits) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Holding time
        holding_times = [t.holding_time_ms() for t in strategy_trades if t.exit_time]
        avg_holding_time = np.median(holding_times) if holding_times else 0
        
        # Best/worst
        best_trade = max(profits)
        worst_trade = min(profits)
        
        # Consecutive wins/losses
        consecutive_wins = self._max_consecutive(strategy_trades, True)
        consecutive_losses = self._max_consecutive(strategy_trades, False)
        
        return StrategyPerformance(
            strategy_name=strategy_name,
            opportunities_count=len(strategy_trades),
            win_rate=win_rate,
            total_profit_usd=total_profit,
            avg_profit_usd=avg_profit,
            sharpe_ratio=sharpe,
            avg_holding_time_ms=avg_holding_time,
            best_trade_usd=best_trade,
            worst_trade_usd=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
        )
    
    def _max_consecutive(self, trades: List[Trade], success: bool) -> int:
        """Calculate maximum consecutive wins or losses"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade.success == success:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def get_profit_distribution(self, days: int = 30) -> Dict:
        """Get profit distribution statistics"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_trades = [t for t in self.trades if t.timestamp >= cutoff]
        
        if not recent_trades:
            return {"count": 0}
        
        profits = [t.profit_usd for t in recent_trades]
        
        # Distribution fit
        if len(profits) > 3:
            skewness = stats.skew(profits)
            kurtosis = stats.kurtosis(profits)
        else:
            skewness = 0
            kurtosis = 0
        
        # Percentiles
        percentiles = np.percentile(profits, [5, 25, 50, 75, 95])
        
        return {
            "count": len(profits),
            "mean": np.mean(profits),
            "std": np.std(profits),
            "min": np.min(profits),
            "max": np.max(profits),
            "p5": percentiles[0],
            "p25": percentiles[1],
            "p50": percentiles[2],
            "p75": percentiles[3],
            "p95": percentiles[4],
            "skewness": skewness,
            "kurtosis": kurtosis,
        }
    
    def compare_strategies(self, days: int = 30) -> List[StrategyPerformance]:
        """Compare all strategies"""
        # Get unique strategy names
        strategy_names = list(set(t.strategy_name for t in self.trades))
        
        performances = []
        for name in strategy_names:
            perf = self.analyze_strategy_performance(name, days)
            if perf:
                performances.append(perf)
        
        # Sort by total profit
        performances.sort(key=lambda p: p.total_profit_usd, reverse=True)
        
        return performances
    
    def get_statistics(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "total_trades": len(self.trades),
            "opportunities_seen": self.opportunities_seen,
            "capture_rate": (
                len(self.trades) / self.opportunities_seen * 100
                if self.opportunities_seen > 0 else 0
            ),
            "risk_free_rate": self.risk_free_rate,
        }
