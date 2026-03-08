"""
Tests for AME v3.0 modules
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestLiquidityGraph:
    """Tests for LiquidityGraphEngine"""

    def test_graph_initialization(self):
        """Test graph engine initialization"""
        from core.liquidity_graph import LiquidityGraphEngine
        
        engine = LiquidityGraphEngine(max_hop_count=6, min_liquidity_usd=50000)
        
        assert engine.max_hop_count == 6
        assert engine.min_liquidity_usd == 50000
        assert engine.adjacency is not None  # FIXED: Use adjacency instead of graph
        assert engine.pools_by_pair is not None  # FIXED: Multi-pool support
    
    def test_add_token(self):
        """Test adding tokens to graph"""
        from core.liquidity_graph import Token, LiquidityGraphEngine
        
        engine = LiquidityGraphEngine()
        token = Token(
            address="token1",
            symbol="SOL",
            name="Solana",
            decimals=9,
        )
        
        engine.add_token(token)
        
        assert "token1" in engine.tokens
        assert "token1" in engine.adjacency  # FIXED: Check adjacency instead of graph
    
    def test_add_pool(self):
        """Test adding pools to graph"""
        from core.liquidity_graph import Pool, LiquidityGraphEngine
        
        engine = LiquidityGraphEngine()
        
        # Add tokens first
        from core.liquidity_graph import Token
        engine.add_token(Token("token_a", "A", "Token A", 9))
        engine.add_token(Token("token_b", "B", "Token B", 9))
        
        pool = Pool(
            address="pool1",
            dex="raydium",
            token_a="token_a",
            token_b="token_b",
            liquidity_usd=100000,
            price_a_per_b=150.0,
            price_b_per_a=0.0067,
            fee_percent=0.25,
        )
        
        engine.add_pool(pool)
        
        assert "pool1" in engine.pools
        # FIXED: Check adjacency list for edges
        assert "token_a" in engine.adjacency
        assert "token_b" in engine.adjacency
        # Check multi-pool support
        assert "token_a-token_b" in engine.pools_by_pair


class TestScoringEngine:
    """Tests for OpportunityScoringEngine"""

    def test_score_calculation(self):
        """Test opportunity scoring"""
        from core.scoring_engine import OpportunityScoringEngine
        
        engine = OpportunityScoringEngine(min_score=100.0)
        
        score = engine.calculate_score(
            opportunity_id="test_1",
            raw_profit_usd=100.0,
            estimated_costs_usd=20.0,
            competition_level="MEDIUM",
            tip_sol=0.001,
            mempool_density=500,
            current_latency_ms=50,
        )
        
        assert score is not None
        assert score.expected_profit_usd == 80.0
        assert score.score > 0
    
    def test_unprofitable_opportunity(self):
        """Test scoring of unprofitable opportunity"""
        from core.scoring_engine import OpportunityScoringEngine
        
        engine = OpportunityScoringEngine()
        
        score = engine.calculate_score(
            opportunity_id="test_2",
            raw_profit_usd=10.0,
            estimated_costs_usd=50.0,  # Costs > profit
            competition_level="HIGH",
            tip_sol=0.001,
            mempool_density=1000,
            current_latency_ms=100,
        )
        
        assert score is None  # Should reject unprofitable


class TestKillSwitch:
    """Tests for KillSwitchRiskSystem"""

    def test_killswitch_initialization(self):
        """Test kill-switch initialization"""
        from risk.kill_switch import KillSwitchRiskSystem
        
        ks = KillSwitchRiskSystem(
            daily_loss_limit_percent=5.0,
            gas_spike_multiplier=2.0,
        )
        
        assert ks.daily_loss_limit_percent == 5.0
        assert ks.gas_spike_multiplier == 2.0
        assert ks.state.is_active == False
    
    def test_daily_loss_trigger(self):
        """Test daily loss trigger"""
        from risk.kill_switch import KillSwitchRiskSystem
        
        ks = KillSwitchRiskSystem(daily_loss_limit_percent=5.0)
        ks.update_daily_start_balance(10000.0)
        ks.update_daily_pnl(-600.0)  # 6% loss
        
        triggered = ks.check_all()
        
        assert triggered == True
        assert ks.state.is_active == True
        assert ks.state.triggered_by.trigger_type == "daily_loss"
    
    def test_killswitch_cooldown(self):
        """Test kill-switch cooldown"""
        from risk.kill_switch import KillSwitchRiskSystem
        from datetime import timedelta
        
        ks = KillSwitchRiskSystem(cooldown_minutes=1)
        ks.update_daily_start_balance(10000.0)
        ks.update_daily_pnl(-600.0)
        ks.check_all()
        
        # Should still be active
        assert ks.state.is_active == True
        
        # Simulate cooldown (in production: wait actual time)
        ks.state.cooldown_until = datetime.utcnow() - timedelta(minutes=1)
        
        # Should reset on next check
        triggered = ks.check_all()
        assert triggered == False


class TestStrategyLayer:
    """Tests for Strategy Layer"""

    def test_triangular_strategy(self):
        """Test triangular strategy"""
        from strategies.base_strategies import TriangularStrategy, StrategyConfig
        
        strategy = TriangularStrategy(
            StrategyConfig(
                name="triangular_test",
                min_profit_percent=0.1,
            )
        )
        
        assert strategy.config.name == "triangular_test"
        assert strategy.max_hops == 3
    
    def test_cross_dex_strategy(self):
        """Test cross-DEX strategy"""
        from strategies.base_strategies import CrossDEXStrategy, StrategyConfig
        
        strategy = CrossDEXStrategy(
            StrategyConfig(
                name="cross_dex_test",
                min_profit_percent=0.15,
            )
        )
        
        assert strategy.config.name == "cross_dex_test"


class TestCapitalAllocation:
    """Tests for Capital Allocation Engine"""

    def test_optimize_single_opportunity(self):
        """Test single opportunity optimization"""
        from core.capital_allocation import CapitalAllocationEngine
        
        engine = CapitalAllocationEngine(
            total_capital_usd=50000.0,
            max_per_opp_percent=20.0,
        )
        
        # Simple profit function: profit = size * 0.001 (0.1% return)
        def profit_fn(size):
            return size * 0.001
        
        result = engine.optimize_single_opportunity(
            opportunity_id="test_opp",
            profit_function=profit_fn,
            min_size=1000.0,
            max_size=10000.0,
        )
        
        assert result is not None
        assert result.optimal_size_usd > 0
        assert result.expected_profit_usd > 0


class TestSwapSimulation:
    """Tests for Swap Simulation Engine"""

    def test_constant_product_simulation(self):
        """Test constant product AMM simulation"""
        from core.swap_simulation import SwapSimulator, PoolState, AMMType
        
        simulator = SwapSimulator()
        
        pool = PoolState(
            address="pool1",
            amm_type=AMMType.CONSTANT_PRODUCT,
            token_a="SOL",
            token_b="USDC",
            reserve_a=1000.0,
            reserve_b=150000.0,
            fee_percent=0.25,
            price=150.0,
            liquidity=150000000.0,
        )
        
        simulator.add_pool(pool)
        
        quote = simulator.simulate_swap(
            pool_address="pool1",
            input_token="SOL",
            input_amount=10.0,
        )
        
        assert quote is not None
        assert quote.input_amount == 10.0
        assert quote.output_amount > 0
        assert quote.price_impact_percent >= 0


class TestMEVEstimator:
    """Tests for MEV Competition Estimator"""

    def test_competition_estimation(self):
        """Test competition level estimation"""
        from infrastructure.mev_estimator import MEVCompetitionEstimator
        
        estimator = MEVCompetitionEstimator(
            tip_floor_sol=0.001,
            tip_ceiling_sol=0.05,
        )
        
        # Update with some data
        estimator.update_mempool_density(500)
        estimator.update_landed_tip(0.002)
        
        metrics = estimator.estimate_competition_level()
        
        assert metrics.level is not None
        assert metrics.mempool_density == 500
        assert metrics.avg_tip_sol > 0
    
    def test_tip_optimization(self):
        """Test tip optimization"""
        from infrastructure.mev_estimator import MEVCompetitionEstimator
        
        estimator = MEVCompetitionEstimator()
        
        optimization = estimator.optimize_tip(
            expected_profit_sol=1.0,
        )
        
        assert optimization.recommended_tip_sol > 0
        assert optimization.expected_win_rate > 0


class TestPortfolioManager:
    """Tests for Portfolio Manager"""

    def test_open_position(self):
        """Test opening position"""
        from core.portfolio_manager import PortfolioManager, RiskLimits
        
        pm = PortfolioManager(
            initial_capital_usd=50000.0,
            risk_limits=RiskLimits(
                max_per_token_percent=30.0,
            ),
        )
        
        success, msg = pm.open_position(
            token="SOL",
            amount=100.0,
            entry_price=150.0,
            strategy_name="triangular",
        )
        
        assert success == True
        assert "SOL" in pm.positions
        assert pm.positions["SOL"].amount == 100.0
    
    def test_close_position(self):
        """Test closing position"""
        from core.portfolio_manager import PortfolioManager
        
        pm = PortfolioManager(initial_capital_usd=50000.0)
        
        # Open position
        pm.open_position(
            token="SOL",
            amount=100.0,
            entry_price=150.0,
            strategy_name="test",
        )
        
        # Close position (FIXED: add exit_price)
        success, msg, pnl = pm.close_position(
            token="SOL",
            exit_price=160.0,  # FIXED: Added exit_price
        )
        
        assert success == True
        assert "SOL" not in pm.positions  # Fully closed
        # PnL should be profit (160-150)*100 = 1000
        assert pnl > 0  # FIXED: Expect profit


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
