"""
MEV Competition Estimator

Estimate MEV bot competition and optimize tip bidding.

Features:
- Mempool density analysis
- Landed tip tracking
- Competition level estimation (LOW/MEDIUM/HIGH)
- Dynamic tip adjustment
- Success probability prediction

Target: Maximize profit while winning bundle auctions
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from enum import Enum


class CompetitionLevel(Enum):
    """MEV competition levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class CompetitionMetrics:
    """Current competition metrics"""
    level: CompetitionLevel
    mempool_density: float  # Transactions per second
    avg_tip_sol: float  # Average tip in last N bundles
    median_tip_sol: float
    tip_floor_sol: float  # Current minimum tip
    active_bots_estimate: int  # Estimated number of competing bots
    win_rate_estimate: float  # Estimated win rate at current tip
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "mempool_density": self.mempool_density,
            "avg_tip_sol": self.avg_tip_sol,
            "median_tip_sol": self.median_tip_sol,
            "tip_floor_sol": self.tip_floor_sol,
            "active_bots_estimate": self.active_bots_estimate,
            "win_rate_estimate": self.win_rate_estimate,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TipOptimization:
    """Optimal tip recommendation"""
    recommended_tip_sol: float
    expected_win_rate: float
    expected_profit_sol: float
    confidence: float
    reasoning: str
    alternatives: List[Tuple[float, float]] = field(default_factory=list)  # (tip, win_rate) pairs
    
    def to_dict(self) -> dict:
        return {
            "recommended_tip_sol": self.recommended_tip_sol,
            "expected_win_rate": self.expected_win_rate,
            "expected_profit_sol": self.expected_profit_sol,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
        }


class MEVCompetitionEstimator:
    """
    Estimate MEV competition and optimize tips
    
    Data sources:
    - Jito mempool stream
    - Landed bundle tips
    - Historical win rates
    
    Outputs:
    - Competition level (LOW/MEDIUM/HIGH/EXTREME)
    - Optimal tip recommendation
    - Success probability
    """
    
    def __init__(
        self,
        tip_floor_sol: float = 0.001,
        tip_ceiling_sol: float = 0.05,
        max_tip_percent_of_profit: float = 30.0,
    ):
        # Tip constraints
        self.tip_floor_sol = tip_floor_sol
        self.tip_ceiling_sol = tip_ceiling_sol
        self.max_tip_percent_of_profit = max_tip_percent_of_profit
        
        # Historical data
        self.tip_history: List[float] = []
        self.mempool_density_history: List[float] = []
        self.win_rate_history: List[Tuple[float, bool]] = []  # (tip_sol, won)
        self.competition_history: List[CompetitionLevel] = []
        
        # Thresholds (calibrated from historical data)
        self.density_thresholds = {
            CompetitionLevel.LOW: 100,  # tx/sec
            CompetitionLevel.MEDIUM: 300,
            CompetitionLevel.HIGH: 600,
            CompetitionLevel.EXTREME: 1000,
        }
        
        # Tip multipliers by competition level
        self.tip_multipliers = {
            CompetitionLevel.LOW: 1.0,
            CompetitionLevel.MEDIUM: 1.5,
            CompetitionLevel.HIGH: 2.0,
            CompetitionLevel.EXTREME: 3.0,
        }
    
    def update_mempool_density(self, density: float):
        """Update mempool density (transactions per second)"""
        self.mempool_density_history.append(density)
        
        # Keep last 1000 samples
        if len(self.mempool_density_history) > 1000:
            self.mempool_density_history = self.mempool_density_history[-1000:]
    
    def update_landed_tip(self, tip_sol: float):
        """Update landed tip from successful bundle"""
        self.tip_history.append(tip_sol)
        
        # Keep last 100 samples
        if len(self.tip_history) > 100:
            self.tip_history = self.tip_history[-100:]
    
    def update_bundle_result(self, tip_sol: float, won: bool):
        """Update bundle submission result"""
        self.win_rate_history.append((tip_sol, won))
        
        # Keep last 500 samples
        if len(self.win_rate_history) > 500:
            self.win_rate_history = self.win_rate_history[-500:]
    
    def estimate_competition_level(self) -> CompetitionMetrics:
        """
        Estimate current competition level
        
        Returns:
            CompetitionMetrics with current state
        """
        # 1. Analyze mempool density
        if self.mempool_density_history:
            avg_density = np.mean(self.mempool_density_history[-100:])
        else:
            avg_density = 100  # Default
        
        # 2. Analyze tips
        if self.tip_history:
            avg_tip = np.mean(self.tip_history)
            median_tip = np.median(self.tip_history)
        else:
            avg_tip = self.tip_floor_sol
            median_tip = self.tip_floor_sol
        
        # 3. Determine competition level
        level = self._determine_competition_level(avg_density)
        
        # 4. Estimate active bots
        active_bots = self._estimate_active_bots(avg_density, avg_tip)
        
        # 5. Estimate win rate at current tip floor
        win_rate = self._estimate_win_rate(self.tip_floor_sol)
        
        metrics = CompetitionMetrics(
            level=level,
            mempool_density=avg_density,
            avg_tip_sol=avg_tip,
            median_tip_sol=median_tip,
            tip_floor_sol=self.tip_floor_sol,
            active_bots_estimate=active_bots,
            win_rate_estimate=win_rate,
        )
        
        self.competition_history.append(level)
        return metrics
    
    def _determine_competition_level(self, density: float) -> CompetitionLevel:
        """Determine competition level from density"""
        if density < self.density_thresholds[CompetitionLevel.LOW]:
            return CompetitionLevel.LOW
        elif density < self.density_thresholds[CompetitionLevel.MEDIUM]:
            return CompetitionLevel.MEDIUM
        elif density < self.density_thresholds[CompetitionLevel.HIGH]:
            return CompetitionLevel.HIGH
        else:
            return CompetitionLevel.EXTREME
    
    def _estimate_active_bots(
        self,
        density: float,
        avg_tip: float,
    ) -> int:
        """Estimate number of active competing bots"""
        # Simplified heuristic
        # In production: use ML model trained on historical data
        
        base_bots = 5  # Base estimate
        density_factor = density / 100  # More density = more bots
        tip_factor = avg_tip / self.tip_floor_sol  # Higher tips = more competition
        
        estimate = int(base_bots + density_factor * tip_factor * 2)
        return max(1, min(estimate, 100))  # Clamp to [1, 100]
    
    def _estimate_win_rate(self, tip_sol: float) -> float:
        """Estimate win rate at given tip level"""
        if not self.win_rate_history:
            # Default: 50% at floor, increases with tip
            ratio = tip_sol / self.tip_floor_sol
            return min(0.5 + (ratio - 1) * 0.1, 0.95)
        
        # Calculate from recent history
        recent = self.win_rate_history[-100:]
        
        # Group by tip ranges
        similar_tips = [
            (t, w) for t, w in recent
            if abs(t - tip_sol) / tip_sol < 0.5  # Within 50%
        ]
        
        if not similar_tips:
            return 0.5  # No data
        
        wins = sum(1 for _, won in similar_tips if won)
        return wins / len(similar_tips)
    
    def optimize_tip(
        self,
        expected_profit_sol: float,
        competition: CompetitionMetrics = None,
    ) -> TipOptimization:
        """
        Optimize tip for maximum expected profit
        
        Args:
            expected_profit_sol: Expected gross profit in SOL
            competition: Current competition metrics (or None to estimate)
        
        Returns:
            TipOptimization with recommendation
        """
        if competition is None:
            competition = self.estimate_competition_level()
        
        # Maximum affordable tip
        max_tip = expected_profit_sol * self.max_tip_percent_of_profit / 100
        max_tip = min(max_tip, self.tip_ceiling_sol)
        
        # Base tip from competition level
        multiplier = self.tip_multipliers[competition.level]
        base_tip = self.tip_floor_sol * multiplier
        
        # Constrain to affordable range
        optimal_tip = min(base_tip, max_tip)
        optimal_tip = max(optimal_tip, self.tip_floor_sol)
        
        # Estimate win rate at optimal tip
        win_rate = self._estimate_win_rate(optimal_tip)
        
        # Expected profit after tip
        expected_net_profit = expected_profit_sol - optimal_tip
        
        # Generate alternatives
        alternatives = self._generate_alternatives(
            expected_profit_sol,
            competition,
        )
        
        # Reasoning
        reasoning = self._generate_reasoning(
            optimal_tip,
            win_rate,
            competition,
            expected_net_profit,
        )
        
        return TipOptimization(
            recommended_tip_sol=optimal_tip,
            expected_win_rate=win_rate,
            expected_profit_sol=expected_net_profit,
            confidence=0.75,  # Simplified
            reasoning=reasoning,
            alternatives=alternatives,
        )
    
    def _generate_alternatives(
        self,
        expected_profit_sol: float,
        competition: CompetitionMetrics,
    ) -> List[Tuple[float, float]]:
        """Generate alternative tip options"""
        alternatives = []
        
        # Conservative (floor)
        floor_win_rate = self._estimate_win_rate(self.tip_floor_sol)
        alternatives.append((self.tip_floor_sol, floor_win_rate))
        
        # Aggressive (2x optimal)
        aggressive_tip = min(
            self.tip_floor_sol * 2,
            expected_profit_sol * self.max_tip_percent_of_profit / 100,
        )
        aggressive_win_rate = self._estimate_win_rate(aggressive_tip)
        alternatives.append((aggressive_tip, aggressive_win_rate))
        
        return alternatives
    
    def _generate_reasoning(
        self,
        optimal_tip: float,
        win_rate: float,
        competition: CompetitionMetrics,
        expected_net_profit: float,
    ) -> str:
        """Generate human-readable reasoning"""
        level = competition.level.value
        density = competition.mempool_density
        
        if expected_net_profit <= 0:
            return (
                f"Not profitable after tip. "
                f"Competition: {level}, Density: {density:.0f} tx/s. "
                f"Consider skipping this opportunity."
            )
        
        return (
            f"Competition level: {level}. "
            f"Mempool density: {density:.0f} tx/s. "
            f"Recommended tip: {optimal_tip:.4f} SOL "
            f"(win rate: {win_rate*100:.1f}%). "
            f"Expected net profit: {expected_net_profit:.4f} SOL."
        )
    
    def get_statistics(self) -> Dict:
        """Get estimator statistics"""
        if not self.competition_history:
            return {
                "total_estimates": 0,
                "avg_tip_sol": self.tip_floor_sol,
                "avg_win_rate": 0.5,
            }
        
        # Count by level
        level_counts = {}
        for level in CompetitionLevel:
            count = sum(1 for l in self.competition_history if l == level)
            level_counts[level.value] = count
        
        avg_tip = np.mean(self.tip_history) if self.tip_history else self.tip_floor_sol
        
        # Win rate
        if self.win_rate_history:
            wins = sum(1 for _, won in self.win_rate_history if won)
            avg_win_rate = wins / len(self.win_rate_history)
        else:
            avg_win_rate = 0.5
        
        return {
            "total_estimates": len(self.competition_history),
            "level_distribution": level_counts,
            "avg_tip_sol": avg_tip,
            "avg_win_rate": avg_win_rate,
            "tip_floor_sol": self.tip_floor_sol,
            "tip_ceiling_sol": self.tip_ceiling_sol,
            "max_tip_percent": self.max_tip_percent_of_profit,
        }


class TipBidder:
    """
    Automated tip bidding system
    
    Integrates with:
    - MEVCompetitionEstimator
    - Execution Engine
    - Jito Bundle API
    """
    
    def __init__(
        self,
        estimator: MEVCompetitionEstimator,
        auto_adjust: bool = True,
    ):
        self.estimator = estimator
        self.auto_adjust = auto_adjust
        self.last_tip_sol: float = estimator.tip_floor_sol
    
    async def calculate_tip(
        self,
        opportunity_profit_sol: float,
    ) -> float:
        """
        Calculate optimal tip for opportunity
        
        Args:
            opportunity_profit_sol: Expected profit in SOL
        
        Returns:
            Optimal tip in SOL
        """
        # Get competition estimate
        competition = self.estimator.estimate_competition_level()
        
        # Optimize tip
        optimization = self.estimator.optimize_tip(
            expected_profit_sol=opportunity_profit_sol,
            competition=competition,
        )
        
        # Update last tip
        self.last_tip_sol = optimization.recommended_tip_sol
        
        return optimization.recommended_tip_sol
    
    async def submit_bundle_with_tip(
        self,
        bundle_txs: List,
        tip_sol: float,
    ) -> Tuple[bool, str]:
        """
        Submit bundle with tip (placeholder)
        
        In production:
        1. Build Jito bundle
        2. Add tip transaction
        3. Submit to relay
        4. Wait for confirmation
        
        Args:
            bundle_txs: List of transactions
            tip_sol: Tip amount
        
        Returns:
            (success, bundle_id)
        """
        # Placeholder - always succeeds
        await asyncio.sleep(0.1)
        
        # Record result for learning
        bundle_id = "placeholder_bundle_id"
        won = True  # Simulated
        
        self.estimator.update_bundle_result(tip_sol, won)
        
        return True, bundle_id
    
    def get_statistics(self) -> Dict:
        """Get bidder statistics"""
        return {
            "auto_adjust": self.auto_adjust,
            "last_tip_sol": self.last_tip_sol,
            "estimator_stats": self.estimator.get_statistics(),
        }


# Import asyncio for async functions
import asyncio
