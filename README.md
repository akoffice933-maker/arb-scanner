# 🚀 Arbitrage Scanner & AME v3.0

**Hedge-Fund Grade MEV Arbitrage System for Solana & Base (2026)**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-compose-latest-green.svg)](https://docs.docker.com/compose/)
[![CI/CD](https://github.com/akoffice933-maker/arb-scanner/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/akoffice933-maker/arb-scanner/actions/workflows/ci-cd.yml)
[![Contributors](https://img.shields.io/github/contributors/akoffice933-maker/arb-scanner)](https://github.com/akoffice933-maker/arb-scanner/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/akoffice933-maker/arb-scanner)](https://github.com/akoffice933-maker/arb-scanner/commits/main)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/akoffice933-maker/arb-scanner/releases)

---

## 📋 Quick Navigation

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Phase 1: arb-scanner (Monitoring)](#-phase-1-arb-scanner-monitoring)
- [Phase 2: AME v3.0 (Execution)](#-phase-2-ame-v30-execution)
- [Quick Start](#-quick-start)
- [Performance Metrics](#-performance-metrics)
- [Infrastructure Budget](#-infrastructure-budget)
- [Development Roadmap](#-development-roadmap)
- [Contributing](#-contributing)

---

## 🎯 Overview

**Arbitrage Scanner** — это полноценная MEV-ориентированная арбитражная система уровня prop-trading / hedge-fund для сетей **Solana** и **Base** в 2026 году.

Система состоит из двух фаз:

| Фаза | Название | Статус | Описание |
|------|----------|--------|----------|
| **Phase 1** | `arb-scanner` | ✅ Production Ready | Мониторинг и сбор статистики |
| **Phase 2** | `AME v3.0` | 🚧 In Development | Исполнительный MEV-движок |

### Ключевые возможности

| Возможность | Phase 1 | Phase 2 |
|-------------|---------|---------|
| **Сканирование** | ✅ ~500ms | ✅ <30–80ms p95 |
| **Стратегии** | Базовый спред | Multi-hop, backrun, liquidation, JIT |
| **MEV Protection** | ❌ | ✅ Jito Bundles, Flashbots |
| **Risk Management** | Логирование | Kill-switch, portfolio mgmt |
| **Язык** | Python | Rust (core) + Python (analytics) |

### Производительность

| Метрика | Phase 1 | Phase 2 Target |
|---------|---------|----------------|
| **Latency p95** | ~500ms | <30–80ms |
| **Throughput** | ~2 scans/sec | >500k updates/sec |
| **Profit Accuracy** | ~90% | >97% |
| **Success Rate** | N/A | >70% |

---

## 🏗️ System Architecture

### High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           MARKET DATA LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ ShredStream │  │  Mempool    │  │  Multi-RPC  │  │  Orderflow      │ │
│  │  (Solana)   │  │  Watcher    │  │  Failover   │  │  Analyzer       │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │
│         │                │                │                   │          │
│         └────────────────┴────────────────┴───────────────────┘          │
│                                  │                                       │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    LIQUIDITY GRAPH ENGINE                           │ │
│  │  Tokens as nodes, pools as edges, log-prices as weights            │ │
│  │  Bellman-Ford negative cycle detection (multi-hop до 6)            │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      STRATEGY LAYER                                 │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │ │
│  │  │Triangular│ │Cross-DEX │ │Backrun   │ │Liquidation / JIT     │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘  │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                   SWAP SIMULATION ENGINE                            │ │
│  │  simulate_swap(amount) с CLMM / constant product / V3 ticks        │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │               PROFIT & RISK MODEL                                   │ │
│  │  Profit = gross - fees - slippage - gas - tip - MEV_haircut        │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              OPPORTUNITY SCORING ENGINE                             │ │
│  │  score = expected_profit × success_prob / latency_risk             │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              CAPITAL ALLOCATION ENGINE                              │ │
│  │  Optimal trade size: maximize_profit(amount) via Newton-Raphson    │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │         OPPORTUNITY QUEUE + PRIORITY SCHEDULER                      │ │
│  │  FIFO + score-based sorting, batch processing                      │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              PORTFOLIO / GLOBAL CAPITAL MANAGER                     │ │
│  │  Opp selection при limited capital, risk constraints               │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                  EXECUTION ENGINE                                   │ │
│  │  Bundle/tx builder + tip bidding optimizer                         │ │
│  └────────────────────────────┬───────────────────────────────────────┘ │
│                               │                                         │
│                               ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              PRIVATE RELAY LAYER                                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │ │
│  │  │ Jito Bundles │  │ Flashbots    │  │ MEV Competition Estimator│ │ │
│  │  │  (Solana)    │  │ (Base)       │  │ (dynamic tip adjustment) │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                   RISK & ANALYTICS LAYER                              ││
│  │  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  ││
│  │  │ Kill-Switch  │  │ Historical Alpha │  │ Advanced Telemetry    │  ││
│  │  │ (auto-stop)  │  │ (profit dist,    │  │ (latency heatmaps,    │  ││
│  │  │              │  │  win rate, edge) │  │  success rate)        │  ││
│  │  └──────────────┘  └──────────────────┘  └───────────────────────┘  ││
│  └──────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Phase 1: arb-scanner (Monitoring)

**Статус:** ✅ Production Ready

### Возможности

- 🔍 **Сканирование в реальном времени** — ~2 скана в секунду
- 🌐 **Multi-RPC с Failover** — автоматическое переключение между нодами
- 📊 **Умный расчёт спреда** — с учётом всех комиссий и проскальзывания
- 💾 **PostgreSQL + TimescaleDB** — эффективное хранение временных рядов
- 📈 **Prometheus метрики** — полный мониторинг производительности
- 📱 **Telegram алерты** — мгновенные уведомления о выгодных возможностях
- 🖥️ **Grafana дашборд** — визуализация всех метрик
- 🐳 **Docker** — готовая инфраструктура для развёртывания

### Структура

```
arb-scanner/
├── config/              # Конфигурация
│   └── settings.py
├── core/                # Бизнес-логика
│   ├── scanner.py
│   ├── spread_calculator.py
│   └── pool_tracker.py
├── infrastructure/      # Инфраструктура
│   ├── rpc_manager.py
│   └── shredstream.py
├── storage/             # Работа с БД
│   ├── database.py
│   └── models.py
├── monitoring/          # Мониторинг
│   ├── metrics.py
│   └── alerts.py
├── dashboard/           # Grafana дашборды
│   └── grafana.json
├── tests/               # Тесты
│   └── test_scanner.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── main.py
```

### Быстрый старт

```bash
# Клонирование
git clone https://github.com/akoffice933-maker/arb-scanner.git
cd arb-scanner

# Настройка
cp .env.example .env
# Отредактируйте .env (укажите RPC ключи)

# Запуск через Docker
docker-compose up -d

# Логи
docker-compose logs -f scanner
```

**Полная документация:** [README.md](README.md)

---

## 🚀 Phase 2: AME v3.0 (Execution)

**Статус:** 🚧 In Development (Alpha)

### Архитектура

AME v3.0 — это полноценная MEV-ориентированная арбитражная система уровня hedge-fund.

#### Ключевые компоненты

| Компонент | Описание | Статус |
|-----------|----------|--------|
| **Liquidity Graph** | Graph-based liquidity tracking + Bellman-Ford | ✅ Alpha |
| **Scoring Engine** | Risk-adjusted opportunity scoring | ✅ Alpha |
| **Kill-Switch** | Auto-stop on losses/danger | ✅ Alpha |
| **Strategy Layer** | Modular strategies (triangular, cross-DEX, backrun) | 🚧 Planned |
| **Capital Allocation** | Optimal trade size optimization | 🚧 Planned |
| **Execution Engine** | Bundle builder + tip optimizer | 🚧 Planned |
| **MEV Competition** | Dynamic tip adjustment | 🚧 Planned |

#### Производительность

| Метрика | Target |
|---------|--------|
| **Latency p95** | <30–80ms |
| **Throughput** | >500k updates/sec |
| **Profit Accuracy** | >97% |
| **Success Rate** | >70% |

#### Структура

```
ame-v3/
├── core/
│   ├── liquidity_graph.py   # Graph engine + Bellman-Ford
│   └── scoring_engine.py    # Opportunity scoring
├── risk/
│   └── kill_switch.py       # Auto-stop risk system
├── strategies/              # Modular strategies
├── execution/               # Bundle builder, tip optimizer
├── analytics/               # Historical alpha, telemetry
├── infrastructure/          # RPC, Redis, DB
├── config/
│   └── settings.py          # 200+ hedge-fund settings
├── tests/
├── README.md
└── requirements.txt
```

### Пример использования

```python
from core.liquidity_graph import LiquidityGraphEngine
from core.scoring_engine import OpportunityScoringEngine
from risk.kill_switch import KillSwitchRiskSystem

# Initialize graph engine
graph = LiquidityGraphEngine(max_hop_count=6, min_liquidity_usd=50000)

# Add pools
graph.add_pool(pool_data)

# Detect arbitrage opportunities
opportunities = graph.detect_arbitrage_opportunities()

# Score opportunities
scorer = OpportunityScoringEngine()
for opp in opportunities:
    score = scorer.calculate_score(
        opportunity_id=opp.id,
        raw_profit_usd=opp.profit_usd,
        estimated_costs_usd=opp.costs,
        competition_level="MEDIUM",
        tip_sol=0.001,
        mempool_density=500,
        current_latency_ms=50,
    )
    if score and score.score > 100:
        print(f"✅ Opportunity: score={score.score}, profit=${score.expected_profit_usd}")

# Risk management
kill_switch = KillSwitchRiskSystem(daily_loss_limit_percent=5.0)
if kill_switch.check_all():
    print("🚨 Kill-switch triggered — STOP TRADING")
```

**Полная документация:** [ame-v3/README.md](ame-v3/README.md)

---

## ⚡ Quick Start

### Phase 1: Monitoring (Production)

```bash
# Clone repository
git clone https://github.com/akoffice933-maker/arb-scanner.git
cd arb-scanner

# Setup environment
cp .env.example .env
# Edit .env with your RPC keys

# Run with Docker
docker-compose up -d

# View logs
docker-compose logs -f scanner

# Access Grafana
open http://localhost:3000  # admin/admin123
```

### Phase 2: Execution (Alpha)

```bash
# Navigate to AME v3.0
cd ame-v3

# Install dependencies
pip install -r requirements.txt

# Run example
python -m core.liquidity_graph
```

---

## 📈 Performance Metrics

### Phase 1 (Monitoring)

| Метрика | Значение |
|---------|----------|
| **Scan Frequency** | ~2 scans/sec |
| **Scan Duration** | ~400–500ms |
| **RPC Latency** | <100ms (with failover) |
| **Opportunity Lifetime** | ~150–500ms |
| **Database Write** | <50ms (async) |

### Phase 2 (Targets)

| Метрика | Target |
|---------|--------|
| **Latency p50** | <30ms |
| **Latency p95** | <80ms |
| **Latency p99** | <150ms |
| **Throughput** | >500k updates/sec |
| **Profit Accuracy** | >97% |
| **Execution Success** | >70% |

---

## 💰 Infrastructure Budget

### Phase 1: Monitoring

| Tier | Cost/Month | Components |
|------|------------|------------|
| **Minimum** | ~$10 | VPS $5-10, Free RPC tiers |
| **Optimal** | ~$200 | VPS $40-80, Paid RPC $98, Tips $50 |
| **Professional** | ~$2000 | Dedicated $500, Multi-RPC $600, Tips $800 |

### Phase 2: Execution (Estimated)

| Tier | Cost/Month | Components |
|------|------------|------------|
| **Startup** | ~$500 | Colocation $200, Dedicated RPC $200, Tips $100 |
| **Growth** | ~$5000 | Bare-metal $1000, Multi-RPC $1000, Tips $3000 |
| **Institutional** | ~$50000+ | Multi-region, Private RPC, High tips |

**ROI Expectations (2026):**
- **Phase 1:** $150–600/month (minimum), $1500–6000/month (optimal)
- **Phase 2:** $5000–50000+/month (execution-dependent)

> ⚠️ **Реалии 2026:** Конкуренция высокая, edge выжат. Ожидайте прибыль в нижнем диапазоне.

---

## 🗺️ Development Roadmap

### Phase 1: Monitoring ✅ (Complete)

- [x] Basic scanning (~2 scans/sec)
- [x] Multi-RPC failover
- [x] Smart spread calculation
- [x] PostgreSQL + TimescaleDB
- [x] Prometheus metrics
- [x] Telegram alerts
- [x] Grafana dashboard
- [x] CI/CD with GitHub Actions
- [x] Docker support

### Phase 2: Execution (Alpha) 🚧 (In Progress)

- [x] Liquidity Graph Engine
- [x] Opportunity Scoring Engine
- [x] Kill-Switch Risk System
- [x] Comprehensive configuration
- [ ] Executive bot (Execution Engine)
- [ ] Jupiter Aggregator support
- [ ] Route optimization
- [ ] Backtesting framework
- [ ] Execution simulation
- [ ] Strategy Layer (triangular, cross-DEX, backrun)
- [ ] Capital Allocation Engine
- [ ] Opportunity Queue + Scheduler
- [ ] Portfolio Manager
- [ ] MEV Competition Estimator
- [ ] Tip Bidding Optimizer
- [ ] Rust core migration
- [ ] Historical Alpha Analysis
- [ ] Advanced Telemetry

### Phase 3: Expansion 📋 (Planned)

- [ ] Ethereum support
- [ ] Arbitrum support
- [ ] Flashbots integration (Base)
- [ ] Web dashboard (React)
- [ ] REST API (FastAPI)
- [ ] Multi-region deployment
- [ ] Advanced ML predictions
- [ ] Cross-chain bridges (Wormhole)

### Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| **Phase 1** | 4 weeks | ✅ Complete |
| **Phase 2 (Core)** | 8–10 weeks | 🚧 In Progress |
| **Phase 2 (Execution)** | 8–10 weeks | 📋 Planned |
| **Phase 2 (Testing)** | 4 weeks | 📋 Planned |
| **Phase 3 (Expansion)** | 12–16 weeks | 📋 Planned |

**Total Estimated:** 36–44 weeks (8–10 months)

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas Needing Contribution

- [ ] More DEX integrations (Meteora, Cykura)
- [ ] Backtesting framework
- [ ] Strategy plugins (triangular, backrun, liquidation)
- [ ] Rust core implementation
- [ ] Web dashboard
- [ ] REST API
- [ ] More unit tests
- [ ] Documentation translations

### Development Setup

```bash
# Clone repository
git clone https://github.com/akoffice933-maker/arb-scanner.git
cd arb-scanner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run linters
black --check .
flake8 .
mypy .
```

---

## 📞 Support

- **GitHub Issues:** [Report a bug](https://github.com/akoffice933-maker/arb-scanner/issues)
- **Discussions:** [Ask a question](https://github.com/akoffice933-maker/arb-scanner/discussions)
- **Security:** [Report vulnerability](SECURITY.md)

---

## ⚠️ Disclaimers

1. **Not financial advice** — Use at your own risk
2. **Losses possible** — Slippage, failed transactions, bugs
3. **Test on testnet** — Before mainnet deployment
4. **Monitor RPC limits** — Free tiers have restrictions
5. **Secure your keys** — Never commit `.env` or keys

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📊 Repository Stats

[![Star History Chart](https://api.star-history.com/svg?repos=akoffice933-maker/arb-scanner&type=Date)](https://star-history.com/#akoffice933-maker/arb-scanner&Date)

### Recent Activity

- **Latest Release:** v0.3.0 — AME v3.0 Integration (Phase 2)
- **Total Commits:** 15+
- **Contributors:** 1
- **Stars:** Growing 🌟
- **Last Commit:** Active development

---

**Version:** 0.3.0 (AME v3.0 Alpha)  
**Last Updated:** Март 2026  
**Status:** Phase 1 Production Ready, Phase 2 In Development

---

**Made with ❤️ by akoffice933-maker**  
**Built for Solana & Base MEV in 2026**
