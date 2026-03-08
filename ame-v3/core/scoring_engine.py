"""
Opportunity Scoring Engine

score = expected_profit × success_probability / latency_risk

Target: Maximize risk-adjusted returns
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np


@dataclass
class OpportunityScore:
    """Scored opportunity"""
    opportunity_id: str
    raw_profit_usd: float
    expected_profit_usd: float
    success_probability: float
    latency_risk: float
    score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "raw_profit_usd": self.raw_profit_usd,
            "expected_profit_usd": self.expected_profit_usd,
            "success_probability": self.success_probability,
            "latency_risk": self.latency_risk,
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
        }


class OpportunityScoringEngine:
    """
    Score opportunities for optimal capital allocation
    
    Formula:
        score = expected_profit × success_prob / latency_risk
    
    Components:
    - expected_profit: Net profit after all costs
    - success_probability: f(competition, tip, mempool state)
    - latency_risk: Based on p95 end-to-end latency
    """
    
    def __init__(
        self,
        profit_weight: float = 1.0,
        success_prob_weight: float = 0.5,
        latency_risk_weight: float = 0.3,
        min_score: float = 100.0,
    ):
        self.profit_weight = profit_weight
        self.success_prob_weight = success_prob_weight
        self.latency_risk_weight = latency_risk_weight
        self.min_score = min_score
        
        # Historical data for calibration
        self.historical_success_rates: Dict[str, List[float]] = {}
        self.historical_latencies: Dict[str, List[float]] = {}
    
    def calculate_score(
        self,
        opportunity_id: str,
        raw_profit_usd: float,
        estimated_costs_usd: float,
        competition_level: str,
        tip_sol: float,
        mempool_density: float,
        current_latency_ms: float,
        target_latency_p95_ms: float = 80.0,
    ) -> Optional[OpportunityScore]:
        """
        Calculate opportunity score
        
        Args:
            opportunity_id: Unique identifier
            raw_profit_usd: Gross profit before costs
            estimated_costs_usd: Total costs (fees, gas, tip, slippage)
            competition_level: LOW/MEDIUM/HIGH
            tip_sol: Jito tip amount
            mempool_density: Mempool transaction density
            current_latency_ms: Current end-to-end latency
            target_latency_p95_ms: Target p95 latency
        
        Returns:
            OpportunityScore or None if below threshold
        """
        # 1. Calculate expected profit
        expected_profit_usd = raw_profit_usd - estimated_costs_usd
        
        if expected_profit_usd <= 0:
            return None
        
        # 2. Calculate success probability
        success_prob = self._calculate_success_probability(
            competition_level=competition_level,
            tip_sol=tip_sol,
            mempool_density=mempool_density,
        )
        
        # 3. Calculate latency risk
        latency_risk = self._calculate_latency_risk(
            current_latency_ms=current_latency_ms,
            target_latency_p95_ms=target_latency_p95_ms,
        )
        
        # Avoid division by zero
        if latency_risk == 0:
            latency_risk = 0.01
        
        # 4. Calculate score
        score = (
            expected_profit_usd * self.profit_weight
            * success_prob * self.success_prob_weight
            / (latency_risk * self.latency_risk_weight)
        )
        
        # 5. Check minimum threshold
        if score < self.min_score:
            return None
        
        return OpportunityScore(
            opportunity_id=opportunity_id,
            raw_profit_usd=raw_profit_usd,
            expected_profit_usd=expected_profit_usd,
            success_probability=success_prob,
            latency_risk=latency_risk,
            score=score,
        )
    
    def _calculate_success_probability(
        self,
        competition_level: str,
        tip_sol: float,
        mempool_density: float,
    ) -> float:
        """
        Calculate success probability based on competition and tip
        
        Returns:
            Probability 0.0 to 1.0
        """
        # Base probability
        base_prob = 0.8
        
        # Competition adjustment
        competition_factors = {
            "LOW": 1.0,
            "MEDIUM": 0.85,
            "HIGH": 0.65,
        }
        comp_factor = competition_factors.get(competition_level, 0.8)
        
        # Tip efficiency (higher tip = higher success)
        tip_floor = 0.001  # SOL
        tip_factor = min(tip_sol / tip_floor, 2.0)  # Cap at 2x
        tip_factor = max(tip_factor, 0.5)  # Floor at 0.5x
        
        # Mempool density (higher density = more competition)
        density_factor = 1.0 / (1.0 + mempool_density / 1000)
        
        # Combined probability
        success_prob = base_prob * comp_factor * tip_factor * density_factor
        
        # Clamp to [0.0, 1.0]
        return np.clip(success_prob, 0.0, 1.0)
    
    def _calculate_latency_risk(
        self,
        current_latency_ms: float,
        target_latency_p95_ms: float,
    ) -> float:
        """
        Calculate latency risk
        
        Returns:
            Risk factor (lower is better)
        """
        if current_latency_ms <= target_latency_p95_ms:
            return 0.1  # Low risk
        
        # Exponential penalty for exceeding target
        ratio = current_latency_ms / target_latency_p95_ms
        risk = 0.1 * (ratio ** 2)
        
        return min(risk, 10.0)  # Cap at 10.0
    
    def update_historical_data(
        self,
        opportunity_id: str,
        success: bool,
        latency_ms: float,
    ):
        """Update historical success rates for calibration"""
        if opportunity_id not in self.historical_success_rates:
            self.historical_success_rates[opportunity_id] = []
            self.historical_latencies[opportunity_id] = []
        
        self.historical_success_rates[opportunity_id].append(1.0 if success else 0.0)
        self.historical_latencies[opportunity_id].append(latency_ms)
        
        # Keep last 1000 samples
        if len(self.historical_success_rates[opportunity_id]) > 1000:
            self.historical_success_rates[opportunity_id] = \
                self.historical_success_rates[opportunity_id][-1000:]
            self.historical_latencies[opportunity_id] = \
                self.historical_latencies[opportunity_id][-1000:]
    
    def get_average_success_rate(self, opportunity_id: str) -> float:
        """Get historical success rate for opportunity type"""
        if opportunity_id not in self.historical_success_rates:
            return 0.8  # Default
        
        rates = self.historical_success_rates[opportunity_id]
        return np.mean(rates) if rates else 0.8
    
    def get_statistics(self) -> dict:
        """Get scoring engine statistics"""
        return {
            "min_score": self.min_score,
            "profit_weight": self.profit_weight,
            "success_prob_weight": self.success_prob_weight,
            "latency_risk_weight": self.latency_risk_weight,
            "tracked_opportunities": len(self.historical_success_rates),
        }
