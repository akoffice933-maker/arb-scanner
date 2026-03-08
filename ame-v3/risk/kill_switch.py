"""
Kill-Switch Risk System

Auto-stop on:
- Daily loss limit (>5-10%)
- Gas spike (>2x avg)
- RPC outage (>60 sec)
- Bundle fail rate (>50%)
- Latency spike (p95 >200ms)
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio


@dataclass
class KillSwitchTrigger:
    """Trigger event for kill-switch"""
    trigger_type: str
    threshold: float
    current_value: float
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    message: str = ""


@dataclass
class KillSwitchState:
    """Current state of kill-switch"""
    is_active: bool = False
    triggered_by: Optional[KillSwitchTrigger] = None
    triggered_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


class KillSwitchRiskSystem:
    """
    Automatic risk management system
    
    Triggers:
    - Daily loss limit
    - Gas spike
    - RPC outage
    - Bundle fail rate
    - Latency spike
    
    Actions:
    - Stop all trading
    - Revert pending bundles
    - Enter cooldown period
    """
    
    def __init__(
        self,
        daily_loss_limit_percent: float = 5.0,
        gas_spike_multiplier: float = 2.0,
        rpc_timeout_sec: int = 60,
        bundle_fail_rate_percent: float = 50.0,
        latency_p95_threshold_ms: float = 200.0,
        cooldown_minutes: int = 5,
    ):
        # Thresholds
        self.daily_loss_limit_percent = daily_loss_limit_percent
        self.gas_spike_multiplier = gas_spike_multiplier
        self.rpc_timeout_sec = rpc_timeout_sec
        self.bundle_fail_rate_percent = bundle_fail_rate_percent
        self.latency_p95_threshold_ms = latency_p95_threshold_ms
        self.cooldown_minutes = cooldown_minutes
        
        # State
        self.state = KillSwitchState()
        
        # Metrics tracking
        self.daily_pnl_usd = 0.0
        self.daily_start_balance_usd = 0.0
        self.gas_price_history: List[float] = []
        self.rpc_last_success: Optional[datetime] = None
        self.bundle_results: List[bool] = []  # True=success, False=fail
        self.latency_p95_ms: float = 0.0
        
        # Alert callbacks
        self.on_trigger_callbacks: List[callable] = []
        self.on_reset_callbacks: List[callable] = []
    
    def check_all(self) -> bool:
        """
        Check all kill-switch conditions
        
        Returns:
            True if kill-switch triggered (STOP TRADING)
            False if safe to continue
        """
        # Check if already triggered
        if self.state.is_active:
            # Check cooldown
            if self.state.cooldown_until and datetime.utcnow() > self.state.cooldown_until:
                self._reset()
                return False
            return True
        
        # Check each condition
        triggers = [
            self._check_daily_loss(),
            self._check_gas_spike(),
            self._check_rpc_outage(),
            self._check_bundle_fail_rate(),
            self._check_latency_spike(),
        ]
        
        # Trigger on first failure
        for trigger in triggers:
            if trigger:
                self._trigger(trigger)
                return True
        
        return False
    
    def _check_daily_loss(self) -> Optional[KillSwitchTrigger]:
        """Check daily loss limit"""
        if self.daily_start_balance_usd <= 0:
            return None
        
        loss_percent = abs(self.daily_pnl_usd) / self.daily_start_balance_usd * 100
        
        if loss_percent >= self.daily_loss_limit_percent:
            return KillSwitchTrigger(
                trigger_type="daily_loss",
                threshold=self.daily_loss_limit_percent,
                current_value=loss_percent,
                message=f"Daily loss {loss_percent:.2f}% exceeds limit {self.daily_loss_limit_percent}%",
            )
        
        return None
    
    def _check_gas_spike(self) -> Optional[KillSwitchTrigger]:
        """Check gas price spike"""
        if len(self.gas_price_history) < 10:
            return None
        
        # Calculate average gas (last 10 samples)
        avg_gas = sum(self.gas_price_history[-10:]) / len(self.gas_price_history[-10:])
        current_gas = self.gas_price_history[-1]
        
        if current_gas >= avg_gas * self.gas_spike_multiplier:
            return KillSwitchTrigger(
                trigger_type="gas_spike",
                threshold=self.gas_spike_multiplier,
                current_value=current_gas / avg_gas,
                message=f"Gas spike {current_gas/avg_gas:.2f}x exceeds threshold {self.gas_spike_multiplier}x",
            )
        
        return None
    
    def _check_rpc_outage(self) -> Optional[KillSwitchTrigger]:
        """Check RPC connection outage"""
        if not self.rpc_last_success:
            return None
        
        outage_sec = (datetime.utcnow() - self.rpc_last_success).total_seconds()
        
        if outage_sec >= self.rpc_timeout_sec:
            return KillSwitchTrigger(
                trigger_type="rpc_outage",
                threshold=self.rpc_timeout_sec,
                current_value=outage_sec,
                message=f"RPC outage {outage_sec:.0f}s exceeds timeout {self.rpc_timeout_sec}s",
            )
        
        return None
    
    def _check_bundle_fail_rate(self) -> Optional[KillSwitchTrigger]:
        """Check bundle execution fail rate"""
        if len(self.bundle_results) < 10:
            return None
        
        # Calculate fail rate (last 20 bundles)
        recent = self.bundle_results[-20:]
        fail_count = sum(1 for r in recent if not r)
        fail_rate = fail_count / len(recent) * 100
        
        if fail_rate >= self.bundle_fail_rate_percent:
            return KillSwitchTrigger(
                trigger_type="bundle_fail_rate",
                threshold=self.bundle_fail_rate_percent,
                current_value=fail_rate,
                message=f"Bundle fail rate {fail_rate:.1f}% exceeds threshold {self.bundle_fail_rate_percent}%",
            )
        
        return None
    
    def _check_latency_spike(self) -> Optional[KillSwitchTrigger]:
        """Check latency p95 spike"""
        if self.latency_p95_ms <= 0:
            return None
        
        if self.latency_p95_ms >= self.latency_p95_threshold_ms:
            return KillSwitchTrigger(
                trigger_type="latency_spike",
                threshold=self.latency_p95_threshold_ms,
                current_value=self.latency_p95_ms,
                message=f"Latency p95 {self.latency_p95_ms:.1f}ms exceeds threshold {self.latency_p95_threshold_ms}ms",
            )
        
        return None
    
    def _trigger(self, trigger: KillSwitchTrigger):
        """Trigger kill-switch"""
        self.state.is_active = True
        self.state.triggered_by = trigger
        self.state.triggered_at = datetime.utcnow()
        self.state.cooldown_until = datetime.utcnow() + timedelta(minutes=self.cooldown_minutes)
        
        # Notify callbacks
        for callback in self.on_trigger_callbacks:
            try:
                callback(trigger)
            except Exception:
                pass
        
        print(f"🚨 KILL-SWITCH TRIGGERED: {trigger.message}")
    
    def _reset(self):
        """Reset kill-switch after cooldown"""
        self.state.is_active = False
        self.state.triggered_by = None
        self.state.triggered_at = None
        self.state.cooldown_until = None
        
        # Notify callbacks
        for callback in self.on_reset_callbacks:
            try:
                callback()
            except Exception:
                pass
        
        print("✅ Kill-switch reset, trading resumed")
    
    # =================================================================
    # Metrics Update Methods
    # =================================================================
    
    def update_daily_pnl(self, pnl_usd: float):
        """Update daily PnL"""
        self.daily_pnl_usd = pnl_usd
    
    def update_daily_start_balance(self, balance_usd: float):
        """Update daily starting balance"""
        self.daily_start_balance_usd = balance_usd
    
    def update_gas_price(self, gas_price: float):
        """Update current gas price"""
        self.gas_price_history.append(gas_price)
        if len(self.gas_price_history) > 100:
            self.gas_price_history = self.gas_price_history[-100:]
    
    def update_rpc_success(self):
        """Update last successful RPC call"""
        self.rpc_last_success = datetime.utcnow()
    
    def update_bundle_result(self, success: bool):
        """Update bundle execution result"""
        self.bundle_results.append(success)
        if len(self.bundle_results) > 100:
            self.bundle_results = self.bundle_results[-100:]
    
    def update_latency_p95(self, latency_ms: float):
        """Update p95 latency"""
        self.latency_p95_ms = latency_ms
    
    # =================================================================
    # Callback Registration
    # =================================================================
    
    def on_trigger(self, callback: callable):
        """Register callback for kill-switch trigger"""
        self.on_trigger_callbacks.append(callback)
    
    def on_reset(self, callback: callable):
        """Register callback for kill-switch reset"""
        self.on_reset_callbacks.append(callback)
    
    # =================================================================
    # Status & Diagnostics
    # =================================================================
    
    def get_state(self) -> KillSwitchState:
        """Get current kill-switch state"""
        return self.state
    
    def get_status(self) -> dict:
        """Get status summary"""
        return {
            "is_active": self.state.is_active,
            "triggered_by": self.state.triggered_by.trigger_type if self.state.triggered_by else None,
            "triggered_at": self.state.triggered_at.isoformat() if self.state.triggered_at else None,
            "cooldown_until": self.state.cooldown_until.isoformat() if self.state.cooldown_until else None,
            "daily_pnl_usd": self.daily_pnl_usd,
            "daily_loss_percent": (
                abs(self.daily_pnl_usd) / self.daily_start_balance_usd * 100
                if self.daily_start_balance_usd > 0 else 0
            ),
            "gas_price_current": self.gas_price_history[-1] if self.gas_price_history else 0,
            "rpc_outage_sec": (
                (datetime.utcnow() - self.rpc_last_success).total_seconds()
                if self.rpc_last_success else 0
            ),
            "bundle_fail_rate": (
                sum(1 for r in self.bundle_results[-20:] if not r) / len(self.bundle_results[-20:]) * 100
                if self.bundle_results else 0
            ),
            "latency_p95_ms": self.latency_p95_ms,
        }
