"""
Execution Engine v2 — Realistic Simulation (No Fake Success)

FIXED:
- Removed "always success" mocks
- Proper simulation with failure scenarios
- Realistic success rates based on conditions
- Slippage and gas estimation

Target: Paper/sim-only mode with realistic outcomes
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import random


class ExecutionStatus(Enum):
    """Execution result status"""
    SUCCESS = "success"
    FAILED = "failed"
    REVERTED = "reverted"
    TIMEOUT = "timeout"
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    SLIPPAGE_TOO_HIGH = "slippage_too_high"
    GAS_TOO_HIGH = "gas_too_high"


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    status: ExecutionStatus
    profit_usd: float
    gas_used: float
    slippage_percent: float
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "profit_usd": self.profit_usd,
            "gas_used": self.gas_used,
            "slippage_percent": self.slippage_percent,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "is_success": self.is_success,
        }


@dataclass
class SimulationConfig:
    """Configuration for realistic simulation"""
    base_success_rate: float = 0.85  # 85% base success rate
    slippage_volatility: float = 0.5  # Slippage variance
    gas_volatility: float = 0.3  # Gas price variance
    latency_mean_ms: float = 100.0  # Average latency
    latency_std_ms: float = 50.0  # Latency variance
    revert_rate: float = 0.05  # 5% revert rate
    timeout_rate: float = 0.02  # 2% timeout rate


class ExecutionEngine:
    """
    Execution Engine v2 — Realistic Simulation
    
    Key features:
    - No fake "always success"
    - Realistic failure scenarios
    - Slippage modeling
    - Gas estimation
    - Latency simulation
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        
        # Statistics
        self.executions_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.total_profit_usd = 0.0
        self.total_gas_usd = 0.0
    
    async def execute_trade(
        self,
        opportunity: Dict,
        max_slippage_percent: float = 1.0,
        max_gas_usd: float = 100.0,
    ) -> ExecutionResult:
        """
        Execute trade with realistic simulation
        
        Args:
            opportunity: Opportunity dict with expected_profit_usd, etc.
            max_slippage_percent: Maximum acceptable slippage
            max_gas_usd: Maximum acceptable gas cost
        
        Returns:
            ExecutionResult with realistic outcome
        """
        start_time = datetime.utcnow()
        self.executions_count += 1
        
        # 1. Simulate latency
        latency = self._simulate_latency()
        await asyncio.sleep(latency / 1000)  # Convert to seconds
        
        # 2. Check for random failures
        failure = self._check_random_failure()
        if failure:
            self.failed_count += 1
            return ExecutionResult(
                status=failure,
                profit_usd=0.0,
                gas_used=0.0,
                slippage_percent=0.0,
                error_message=self._get_error_message(failure),
                execution_time_ms=latency,
            )
        
        # 3. Simulate slippage
        slippage = self._simulate_slippage(opportunity)
        
        if slippage > max_slippage_percent:
            self.failed_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SLIPPAGE_TOO_HIGH,
                profit_usd=0.0,
                gas_used=5.0,  # Some gas wasted
                slippage_percent=slippage,
                error_message=f"Slippage {slippage:.2f}% exceeds max {max_slippage_percent:.2f}%",
                execution_time_ms=latency,
            )
        
        # 4. Simulate gas
        gas_cost = self._simulate_gas_cost()
        
        if gas_cost > max_gas_usd:
            self.failed_count += 1
            return ExecutionResult(
                status=ExecutionStatus.GAS_TOO_HIGH,
                profit_usd=0.0,
                gas_used=gas_cost,
                slippage_percent=slippage,
                error_message=f"Gas ${gas_cost:.2f} exceeds max ${max_gas_usd:.2f}",
                execution_time_ms=latency,
            )
        
        # 5. Calculate actual profit (with slippage impact)
        expected_profit = opportunity.get("expected_profit_usd", 0.0)
        slippage_impact = expected_profit * (slippage / 100)
        actual_profit = expected_profit - slippage_impact - gas_cost
        
        # 6. Success!
        self.success_count += 1
        self.total_profit_usd += actual_profit
        self.total_gas_usd += gas_cost
        
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            profit_usd=actual_profit,
            gas_used=gas_cost,
            slippage_percent=slippage,
            execution_time_ms=latency,
        )
    
    def _simulate_latency(self) -> float:
        """Simulate realistic latency"""
        # Normal distribution around mean
        latency = random.gauss(
            self.config.latency_mean_ms,
            self.config.latency_std_ms,
        )
        return max(10.0, latency)  # Min 10ms
    
    def _check_random_failure(self) -> Optional[ExecutionStatus]:
        """Check for random failures"""
        rand = random.random()
        
        # Check revert
        if rand < self.config.revert_rate:
            return ExecutionStatus.REVERTED
        
        # Check timeout
        if rand < self.config.revert_rate + self.config.timeout_rate:
            return ExecutionStatus.TIMEOUT
        
        # Check general failure (based on base success rate)
        if rand > self.config.base_success_rate:
            return ExecutionStatus.FAILED
        
        return None
    
    def _simulate_slippage(self, opportunity: Dict) -> float:
        """Simulate realistic slippage"""
        base_slippage = opportunity.get("estimated_slippage_percent", 0.2)
        
        # Add volatility
        volatility = random.gauss(0, self.config.slippage_volatility)
        slippage = base_slippage + abs(volatility)
        
        return max(0.05, slippage)  # Min 0.05%
    
    def _simulate_gas_cost(self) -> float:
        """Simulate realistic gas cost"""
        base_gas = 10.0  # Base $10
        volatility = random.gauss(0, base_gas * self.config.gas_volatility)
        gas = base_gas + abs(volatility)
        return gas
    
    def _get_error_message(self, status: ExecutionStatus) -> str:
        """Get error message for status"""
        messages = {
            ExecutionStatus.FAILED: "Trade execution failed",
            ExecutionStatus.REVERTED: "Transaction reverted on-chain",
            ExecutionStatus.TIMEOUT: "Transaction timeout",
            ExecutionStatus.INSUFFICIENT_LIQUIDITY: "Insufficient liquidity in pool",
            ExecutionStatus.SLIPPAGE_TOO_HIGH: "Slippage exceeded threshold",
            ExecutionStatus.GAS_TOO_HIGH: "Gas cost exceeded threshold",
        }
        return messages.get(status, "Unknown error")
    
    def get_statistics(self) -> Dict:
        """Get execution statistics"""
        success_rate = (
            self.success_count / self.executions_count * 100
            if self.executions_count > 0 else 0
        )
        
        return {
            "executions_count": self.executions_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "success_rate": success_rate,
            "total_profit_usd": self.total_profit_usd,
            "total_gas_usd": self.total_gas_usd,
            "avg_profit_per_execution": (
                self.total_profit_usd / self.executions_count
                if self.executions_count > 0 else 0
            ),
            "config": {
                "base_success_rate": self.config.base_success_rate,
                "revert_rate": self.config.revert_rate,
                "timeout_rate": self.config.timeout_rate,
            },
        }


class PaperTradingExecutor:
    """
    Paper Trading Executor
    
    Wraps ExecutionEngine for paper trading mode.
    All trades are simulated with realistic outcomes.
    """
    
    def __init__(self, engine: ExecutionEngine = None):
        self.engine = engine or ExecutionEngine()
        self.trades: List[ExecutionResult] = []
    
    async def execute_opportunity(
        self,
        opportunity: Dict,
        max_slippage_percent: float = 1.0,
        max_gas_usd: float = 100.0,
    ) -> ExecutionResult:
        """Execute opportunity in paper mode"""
        result = await self.engine.execute_trade(
            opportunity=opportunity,
            max_slippage_percent=max_slippage_percent,
            max_gas_usd=max_gas_usd,
        )
        
        # Record trade
        self.trades.append(result)
        
        return result
    
    def get_trade_history(self) -> List[ExecutionResult]:
        """Get all executed trades"""
        return self.trades
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if not self.trades:
            return {"total_trades": 0}
        
        successful = [t for t in self.trades if t.is_success]
        failed = [t for t in self.trades if not t.is_success]
        
        return {
            "total_trades": len(self.trades),
            "successful_trades": len(successful),
            "failed_trades": len(failed),
            "success_rate": len(successful) / len(self.trades) * 100,
            "total_profit_usd": sum(t.profit_usd for t in successful),
            "total_gas_usd": sum(t.gas_used for t in self.trades),
            "avg_profit_per_trade": (
                sum(t.profit_usd for t in successful) / len(self.trades)
                if self.trades else 0
            ),
            "avg_slippage_percent": (
                sum(t.slippage_percent for t in self.trades) / len(self.trades)
                if self.trades else 0
            ),
        }
