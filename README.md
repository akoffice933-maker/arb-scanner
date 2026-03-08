# 🚀 Arbitrage Scanner v3.0 — Solana & Base

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-compose-latest-green.svg)](https://docs.docker.com/compose/)
[![CI/CD](https://github.com/akoffice933-maker/arb-scanner/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/akoffice933-maker/arb-scanner/actions/workflows/ci-cd.yml)
[![Contributors](https://img.shields.io/github/contributors/akoffice933-maker/arb-scanner)](https://github.com/akoffice933-maker/arb-scanner/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/akoffice933-maker/arb-scanner)](https://github.com/akoffice933-maker/arb-scanner/commits/main)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Высокоскоростной сканер арбитражных возможностей для децентрализованных бирж (DEX) в сетях Solana и Base.**

> ⚠️ **Phase 1** — Сбор статистики и мониторинг.  
> 🚀 **Phase 2 (AME v3.0)** — Исполнительный MEV-движок (в разработке, см. `ame-v3/`).

---

## 📋 Содержание

- [Описание](#-описание)
- [Возможности](#-возможности)
- [Архитектура](#-архитектура)
- [Быстрый старт](#-быстрый-старт)
- [Подробная настройка](#-подробная-настройка)
- [Запуск в Docker](#-запуск-в-docker)
- [Локальный запуск](#-локальный-запуск)
- [Мониторинг и метрики](#-мониторинг-и-метрики)
- [Telegram уведомления](#-telegram-уведомления)
- [Тестирование](#-тестирование)
- [Добавление новых пулов](#-добавление-новых-пулов)
- [Что НЕ делает сканер](#-что-не-делает-сканер)
- [GO/NO-GO Метрики](#-go/no-go-метрики)
- [Бюджет Инфраструктуры](#-бюджет-инфраструктуры-phase-1)
- [Примеры Запросов](#-примеры-запросов)
- [Примеры Вывода](#-примеры-вывода)
- [AME v3.0 (Phase 2)](#-ame-v30-phase-2--execution-engine)
- [FAQ](#-faq)
- [План развития](#-план-развития)
- [Предупреждения](#-предупреждения)
- [Лицензия](#-лицензия)

---

## 📖 Описание

Arbitrage Scanner v3.0 — это профессиональный инструмент для обнаружения арбитражных возможностей между различными децентрализованными биржами (DEX) в блокчейн-сетях **Solana** и **Base**.

Сканер в реальном времени отслеживает цены на токены в разных пулах ликвидности и вычисляет потенциальную прибыль с учётом всех комиссий:
- Комиссии DEX
- Сетевой газ
- Проскальзывание цены
- Tips валидаторам (Jito для Solana)

### Поддерживаемые DEX

| Сеть | DEX |
|------|-----|
| **Solana** | Raydium, Orca, Jupiter, Meteora |
| **Base** | Aerodrome, Uniswap V3, BaseSwap, AlienBase |

---

## ✨ Возможности

- 🔍 **Сканирование в реальном времени** — ~2 скана в секунду
- 🌐 **Multi-RPC с Failover** — автоматическое переключение между нодами при сбоях
- 📊 **Умный расчёт спреда** — с учётом всех комиссий и проскальзывания
- 💾 **PostgreSQL + TimescaleDB** — эффективное хранение временных рядов
- 📈 **Prometheus метрики** — полный мониторинг производительности
- 📱 **Telegram алерты** — мгновенные уведомления о выгодных возможностях
- 🖥️ **Grafana дашборд** — визуализация всех метрик
- 🐳 **Docker** — готовая инфраструктура для развёртывания

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                      Arbitrage Scanner v3.0                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Solana    │  │    Base     │  │    Jito ShredStream     │ │
│  │   RPC Pool  │  │   RPC Pool  │  │    (MEV Protection)     │ │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘ │
│         │                │                       │              │
│         └────────────────┼───────────────────────┘              │
│                          │                                      │
│                  ┌───────▼────────┐                             │
│                  │  Pool Tracker  │                             │
│                  │  (Real-time)   │                             │
│                  └───────┬────────┘                             │
│                          │                                      │
│                  ┌───────▼────────┐                             │
│                  │   Spread       │                             │
│                  │  Calculator    │                             │
│                  └───────┬────────┘                             │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         │                │                │                     │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐             │
│  │  Database   │  │  Prometheus │  │  Telegram   │             │
│  │  (Timescale)│  │   Metrics   │  │   Alerts    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Структура проекта

```
arb-scanner/
├── config/              # Конфигурация и настройки
│   ├── __init__.py
│   └── settings.py      # Pydantic settings
├── core/                # Бизнес-логика
│   ├── __init__.py
│   ├── scanner.py       # Основной сканер
│   ├── spread_calculator.py  # Калькулятор спреда
│   └── pool_tracker.py  # Трекер пулов
├── infrastructure/      # Внешние подключения
│   ├── __init__.py
│   ├── rpc_manager.py   # Multi-RPC failover
│   └── shredstream.py   # Jito клиент
├── storage/             # Работа с данными
│   ├── __init__.py
│   ├── database.py      # Async PostgreSQL
│   └── models.py        # SQLAlchemy модели
├── monitoring/          # Мониторинг
│   ├── __init__.py
│   ├── metrics.py       # Prometheus метрики
│   └── alerts.py        # Telegram алерты
├── dashboard/           # Визуализация
│   └── grafana.json     # Дашборд для импорта
├── tests/               # Тесты
│   └── test_scanner.py
├── docker-compose.yml   # Docker инфраструктура
├── Dockerfile
├── requirements.txt
├── .env.example
└── main.py
```

---

## ⚡ Быстрый старт

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/akoffice933-maker/arb-scanner.git
cd arb-scanner
```

### Шаг 2: Настройка окружения

```bash
# Скопируйте пример файла окружения
cp .env.example .env
```

### Шаг 3: Запуск через Docker (рекомендуется)

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f scanner

# Остановка
docker-compose down
```

### Шаг 4: Проверка работы

Откройте в браузере:
- **Grafana**: http://localhost:3000 (логин: `admin`, пароль: `admin123`)
- **Prometheus**: http://localhost:9091
- **PostgreSQL**: localhost:5432

---

## 🔧 Подробная настройка

### 1. Настройка RPC нод

Откройте `.env` и настройте RPC эндпоинты:

#### Solana RPC (рекомендуется 3 ноды для failover)

```env
# Основной RPC (Helius)
SOLANA_RPC_PRIMARY=https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_KEY

# Резервный RPC (Alchemy)
SOLANA_RPC_SECONDARY=https://solana-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Третий RPC (Triton/QuickNode)
SOLANA_RPC_TERTIARY=https://mainnet.triton.one/rpc/YOUR_TRITON_KEY
```

**Где получить API ключи:**
- [Helius](https://www.helius.dev/) — бесплатно 100 RPS
- [Alchemy](https://www.alchemy.com/) — бесплатно 300 RPS
- [Triton](https://triton.one/) — бесплатно 100 RPS
- [QuickNode](https://www.quicknode.com/) — платно, высокий лимит

#### Base RPC

```env
# Основной RPC (Alchemy)
BASE_RPC_PRIMARY=https://base-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Резервный RPC (QuickNode)
BASE_RPC_SECONDARY=https://base-mainnet.quicknode.com/YOUR_QUICKNODE_KEY
```

**Где получить API ключи:**
- [Alchemy Base](https://www.alchemy.com/) — бесплатно
- [QuickNode Base](https://www.quicknode.com/) — платно

### 2. Настройка Jito (для Solana)

```env
# UUID вашего Jito bundle
JITO_UUID=your-jito-uuid-here

# Путь к ключу авторизации
JITO_AUTH_KEYPAIR=/app/keypairs/jito.json

# Endpoint ShredStream
SHREDSTREAM_ENDPOINT=mainnet.block-engine.jito.wtf
```

**Как получить Jito UUID:**
1. Зарегистрируйтесь на [Jito Network](https://jito.wtf/)
2. Создайте новый bundle endpoint
3. Скопируйте UUID

### 3. Настройка базы данных

```env
# PostgreSQL подключение
DATABASE_URL=postgresql://arb_user:arb_password@localhost:5432/arb_scanner

# TimescaleDB для временных рядов
TIMESCALE_ENABLED=true
```

### 4. Настройка сканера

```env
# Сети для сканирования (solana, base или обе)
TARGET_NETWORKS=solana,base

# Минимальная ликвидность пула в USD
MIN_LIQUIDITY_USD=50000

# Минимальный спред net для логирования (%)
MIN_SPREAD_NET_PERCENT=0.15

# Максимальное проскальзывание (%)
MAX_SLIPPAGE_PERCENT=2.0

# Таймаут RPC запроса (секунды)
RPC_TIMEOUT_SECONDS=5.0

# Максимум попыток RPC
RPC_MAX_RETRIES=3
```

### 5. Настройка Tips (Jito)

```env
# Макс. процент от прибыли на тип (%)
MAX_TIP_PERCENT_OF_PROFIT=30.0

# Минимальный тип в SOL
TIP_FLOOR_SOL=0.001
```

### 6. Настройка Telegram уведомлений

```env
# Токен бота от @BotFather
TELEGRAM_BOT_TOKEN=1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw

# ID чата для уведомлений (узнать у @userinfobot)
TELEGRAM_CHAT_ID=-1001234567890
```

**Как создать Telegram бота:**
1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя и username бота
4. Скопируйте полученный токен

**Как узнать Chat ID:**
1. Добавьте бота в чат/канал
2. Отправьте любое сообщение
3. Узнайте ID через [@userinfobot](https://t.me/userinfobot)
4. Для канала ID начинается с `-100`

---

## 🐳 Запуск в Docker

### Полный запуск инфраструктуры

```bash
# Запуск всех сервисов (scanner, postgres, prometheus, grafana)
docker-compose up -d

# Проверка статуса
docker-compose ps

# Логи сканера
docker-compose logs -f scanner

# Логи всех сервисов
docker-compose logs -f
```

### Перезапуск после изменений

```bash
# Пересборка и перезапуск
docker-compose up -d --build

# Или только пересоздание контейнера сканера
docker-compose restart scanner
```

### Остановка

```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes (данные БД будут удалены!)
docker-compose down -v
```

### Обновление

```bash
# Pull новых образов
docker-compose pull

# Перезапуск
docker-compose up -d
```

---

## 💻 Локальный запуск

### Требования

- Python 3.11+
- PostgreSQL 15+ с TimescaleDB
- pip или poetry

### Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Установка PostgreSQL + TimescaleDB

#### Windows

1. Скачайте [TimescaleDB Installer](https://docs.timescale.com/install/latest/)
2. Установите с настройками по умолчанию
3. Создайте базу данных:

```sql
CREATE DATABASE arb_scanner;
CREATE USER arb_user WITH PASSWORD 'arb_password';
GRANT ALL PRIVILEGES ON DATABASE arb_scanner TO arb_user;
```

#### Linux (Ubuntu/Debian)

```bash
# Добавление репозитория TimescaleDB
sudo add-apt-repository ppa:timescale/timescaledb-ppa
sudo apt-get update

# Установка
sudo apt-get install timescaledb-2-postgresql-15

# Настройка
sudo timescaledb-tune

# Перезапуск PostgreSQL
sudo systemctl restart postgresql

# Создание БД
sudo -u postgres psql -c "CREATE DATABASE arb_scanner;"
sudo -u postgres psql -c "CREATE USER arb_user WITH PASSWORD 'arb_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE arb_scanner TO arb_user;"
```

#### macOS

```bash
# Установка через Homebrew
brew install timescaledb
brew services start postgresql@15

# Создание БД
createdb arb_scanner
psql -d arb_scanner -c "CREATE USER arb_user WITH PASSWORD 'arb_password';"
psql -d arb_scanner -c "GRANT ALL PRIVILEGES ON DATABASE arb_scanner TO arb_user;"
```

### Запуск сканера

```bash
# Активация виртуального окружения
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Запуск
python main.py
```

### Запуск в фоновом режиме

```bash
# Linux/Mac (nohup)
nohup python main.py > logs/scanner.log 2>&1 &

# Или через screen
screen -S arb-scanner
python main.py
# Ctrl+A, D для открепления
```

---

## 📊 Мониторинг и метрики

### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `arb_scanner_scans_total` | Counter | Всего выполнено сканирований |
| `arb_scanner_opportunities_total` | Counter | Всего найдено возможностей |
| `arb_scanner_scan_duration_seconds` | Histogram | Время выполнения скана |
| `arb_scanner_spread_percent` | Histogram | Распределение спредов |
| `arb_scanner_profit_usd` | Histogram | Распределение прибыли |
| `arb_scanner_rpc_latency_ms` | Gauge | Текущая латентность RPC |
| `arb_scanner_active_pools` | Gauge | Количество активных пулов |
| `arb_scanner_running` | Gauge | Статус сканера (1/0) |
| `arb_scanner_alerts_total` | Counter | Всего отправлено алертов |

### Grafana дашборд

1. Откройте Grafana: http://localhost:3000
2. Логин: `admin`, пароль: `admin123`
3. Dashboard → Import → Upload JSON file
4. Выберите файл `dashboard/grafana.json`
5. Нажмите **Import**

**Включённые панели:**
- Total Opportunities — общее количество возможностей
- Max Profit (Single) — максимальная прибыль
- Scanner Running — статус работы
- Avg RPC Latency — средняя латентность RPC
- Scan Rate — частота сканирования
- RPC Latency by Node — латентность по нодам
- Spread Distribution — распределение спредов
- Profit Distribution — распределение прибыли
- Opportunities by Token — возможности по токенам

---

## 📱 Telegram уведомления

### Типы уведомлений

1. **Запуск сканера** — при старте сервиса
2. **Arbitrage Opportunity** — при обнаружении возможности со спредом > 1%
3. **Остановка сканера** — при корректном завершении
4. **Error Alert** — при критических ошибках

### Пример алерта о возможности

```
🚀 Arbitrage Opportunity Detected!

🪙 Token: SOL
⏰ Time: 2026-03-07 14:30:00

📊 Route:
  Buy: raydium
  Sell: orca

💰 Prices:
  Buy Price: $150.000000
  Sell Price: $152.000000

📈 Spread:
  Gross: 1.33%
  Net: 0.58%

💵 Estimated Profit: $58.00
⛽ Gas + Tip: $0.15

📉 Slippage: 0.20%
⏱️ Lifetime: 150ms
💧 Liquidity: $100,000
```

### Отключение уведомлений

Закомментируйте в `.env`:

```env
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_CHAT_ID=
```

---

## 🧪 Тестирование

### Запуск всех тестов

```bash
# Активация виртуального окружения
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Запуск pytest
pytest tests/ -v
```

### Запуск с покрытием

```bash
# Установка coverage
pip install pytest-cov

# Запуск с отчётом
pytest tests/ --cov=. --cov-report=html

# Открыть отчёт
# Windows
start htmlcov\index.html
# Linux/Mac
open htmlcov/index.html
```

### Запуск отдельных тестов

```bash
# Конкретный тест
pytest tests/test_scanner.py::TestSpreadCalculator::test_calculate_spread_profitable -v

# Тесты по метке
pytest tests/ -m "not slow" -v
```

---

## ➕ Добавление новых пулов

### Solana пулы

Откройте `core/pool_tracker.py` и добавьте в `SOLANA_POOLS`:

```python
SOLANA_POOLS = [
    # ... существующие пулы ...
    {
        "address": "НОВЫЙ_АДРЕС_ПУЛА",
        "dex": "raydium",  # или orca, jupiter, meteora
        "token_a": "АДРЕС_ТОКЕНА_A",
        "token_b": "АДРЕС_ТОКЕНА_B",
        "token_a_symbol": "SOL",
        "token_b_symbol": "USDC",
        "fee_percent": 0.25  # комиссия пула в %
    },
]
```

### Base пулы

Добавьте в `BASE_POOLS`:

```python
BASE_POOLS = [
    # ... существующие пулы ...
    {
        "address": "0xНОВЫЙ_АДРЕС_ПУЛА",
        "dex": "aerodrome",  # или uniswap, baseswap, alienbase
        "token_a": "0xАДРЕС_ТОКЕНА_A",
        "token_b": "0xАДРЕС_ТОКЕНА_B",
        "token_a_symbol": "USDC",
        "token_b_symbol": "ETH",
        "fee_percent": 0.05
    },
]
```

### Где найти адреса пулов

**Solana:**
- [Raydium Pools](https://raydium.io/pools/)
- [Orca Pools](https://www.orca.so/pools)
- [DexScreener Solana](https://dexscreener.com/solana)

**Base:**
- [Aerodrome Pools](https://aerodrome.finance/liquidity)
- [DexScreener Base](https://dexscreener.com/base)

---

## ❓ FAQ

### ❓ Сколько стоит запуск?

| Расход | Стоимость |
|--------|-----------|
| RPC ноды | Бесплатно (с лимитами) или $10-50/мес |
| Сервер | $5-20/мес (VPS) |
| База данных | Бесплатно (локально) |
| Jito Tips | ~0.1-1% от прибыли |

### ❓ Какая минимальная прибыль?

Зависит от настроек:
- `MIN_SPREAD_NET_PERCENT=0.15` — минимум 0.15% net
- При депозите $10,000 это $15 за сделку

### ❓ Как часто находятся возможности?

Зависит от волатильности:
- Спокойный рынок: 5-20 в день
- Волатильный рынок: 50-200+ в день

### ❓ Нужен ли исполнительный бот?

**Phase 1** только сканирует. Для автоматического исполнения нужен отдельный бот (в разработке).

### ❓ Можно ли запустить на Windows?

Да, через Docker Desktop или WSL2.

### ❓ Как увеличить частоту сканирования?

В `core/scanner.py` измените задержку:

```python
await asyncio.sleep(0.5)  # 0.5 = 2 скана/сек
# Измените на 0.25 для 4 сканов/сек
```

⚠️ Учитывайте лимиты RPC!

### ❓ Ошибки подключения к RPC

1. Проверьте API ключи в `.env`
2. Убедитесь, что лимиты не исчерпаны
3. Добавьте больше резервных нод

### ❓ Ошибка TimescaleDB

```sql
-- Включите расширение вручную
psql -U arb_user -d arb_scanner -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
```

---

## 🚀 AME v3.0 (Phase 2) — Execution Engine

**Advanced MEV Arbitrage Engine v3.0** — полноценная исполнительная система уровня hedge-fund.

### Отличия Phase 1 vs Phase 2

| Аспект | arb-scanner (Phase 1) | AME v3.0 (Phase 2) |
|--------|----------------------|-------------------|
| **Цель** | Мониторинг и сбор статистики | Полноценное исполнение |
| **Latency** | ~500ms | <30–80ms p95 |
| **Стратегии** | Базовый спред | Multi-hop, backrun, liquidation, JIT |
| **Risk** | Логирование | Kill-switch, portfolio mgmt |
| **MEV** | Нет | Jito Bundles, competition estimator |
| **Язык** | Python | Rust (core) + Python (analytics) |

### Ключевые компоненты AME v3.0

```
ame-v3/
├── core/
│   ├── liquidity_graph.py    # Graph engine + Bellman-Ford
│   └── scoring_engine.py     # Opportunity scoring
├── risk/
│   └── kill_switch.py        # Auto-stop on losses
├── strategies/               # Modular strategies
├── execution/                # Bundle builder, tip optimizer
├── analytics/                # Historical alpha, telemetry
└── config/
    └── settings.py           # 200+ hedge-fund settings
```

### Производительность

| Метрика | Target |
|---------|--------|
| **Latency p95** | <30–80ms |
| **Throughput** | >500k updates/sec |
| **Profit Accuracy** | >97% |
| **Success Rate** | >70% |

### Запуск AME v3.0

```bash
cd ame-v3
pip install -r requirements.txt
python -m core.liquidity_graph  # Example usage
```

**Полная документация:** [ame-v3/README.md](ame-v3/README.md)

---

## 🗺️ План развития

### Phase 1 ✅ (текущая)
- [x] Базовое сканирование
- [x] Multi-RPC failover
- [x] Расчёт спреда
- [x] База данных
- [x] Метрики Prometheus
- [x] Telegram алерты
- [x] Grafana дашборд

### Phase 2 🚧 (в разработке)
- [ ] Исполнительный бот
- [ ] Поддержка Jupiter Aggregator
- [ ] Оптимизация маршрутов
- [ ] Backtesting
- [ ] Симуляция исполнения

### Phase 3 📋 (планируется)
- [ ] Поддержка Ethereum
- [ ] Поддержка Arbitrum
- [ ] Flashbots интеграция
- [ ] Веб-интерфейс
- [ ] REST API

---

## ❌ Что НЕ делает этот сканер

Важно понимать ограничения проекта:

| НЕ делает | Почему | Альтернатива |
|-----------|--------|--------------|
| ❌ Автоматическое исполнение | Phase 1 только для мониторинга | Phase 2 (в разработке) |
| ❌ Гарантия прибыли | Рынок непредсказуем | Тестируйте на исторических данных |
| ❌ Обход MEV атак | Требуется отдельная защита | Jito Bundle + private RPC |
| ❌ Торговля с кредитным плечом | Только спотовые сделки | Интегрируйте с маржинальными DEX |
| ❌ Поддержка всех DEX | Фокус на ликвидных | Добавляйте пулы вручную |
| ❌ Мгновенное исполнение | Задержки сети и RPC | Оптимизируйте RPC ноды |
| ❌ Работу без настройки | Требуется конфигурация | Следуйте инструкции |

---

## 📊 GO/NO-GO Метрики

Используйте эти метрики для принятия решений об исполнении арбитража:

### ✅ GO (исполнять)

| Метрика | Порог | Значение |
|---------|-------|----------|
| **Spread Net** | > 0.5% | После всех комиссий |
| **Lifetime** | < 500ms | Возможность ещё актуальна |
| **Liquidity** | > $100,000 | Достаточно для входа |
| **RPC Latency** | < 100ms | Нормальная задержка |
| **Tip Floor** | < 0.01 SOL | Разумная комиссия |
| **Slippage** | < 1% | Приемлемое проскальзывание |

### ❌ NO-GO (пропускать)

| Метрика | Порог | Причина |
|---------|-------|---------|
| **Spread Net** | < 0.15% | Недостаточно прибыли |
| **Lifetime** | > 1000ms | Устаревшая возможность |
| **Liquidity** | < $50,000 | Риск высокого проскальзывания |
| **RPC Latency** | > 500ms | Высокий риск неудачи |
| **Tip Floor** | > 0.05 SOL | Слишком дорого |
| **Slippage** | > 3% | Потеря прибыли |

### Пример решения

```python
if (opportunity.spread_net_percent >= 0.5 and
    opportunity.lifetime_ms < 500 and
    opportunity.liquidity_available >= 100000 and
    rpc_manager.get_current_latency() < 100):
    # ✅ GO - исполнять
    await execute_arbitrage(opportunity)
else:
    # ❌ NO-GO - пропустить
    logger.info(f"Skipping: metrics not met")
```

---

## 💰 Бюджет Инфраструктуры (Phase 1)

### Минимальный (~$50/мес)

| Компонент | Стоимость | Примечание |
|-----------|-----------|------------|
| **VPS** | $5-10 | Hetzner, DigitalOcean |
| **Solana RPC** | $0 | Helius free tier (100 RPS) |
| **Base RPC** | $0 | Alchemy free tier (300 RPS) |
| **База данных** | $0 | Локально на VPS |
| **Мониторинг** | $0 | Prometheus + Grafana |
| **Итого** | **~$10/мес** | Для тестирования |

### Оптимальный (~$200/мес)

| Компонент | Стоимость | Примечание |
|-----------|-----------|------------|
| **VPS** | $40-80 | 8 CPU, 16GB RAM, NVMe |
| **Solana RPC** | $49 | Helius Grow (400 RPS) |
| **Solana RPC 2** | $49 | Alchemy Growth (300 RPS) |
| **Base RPC** | $0 | Alchemy free |
| **Jito Tips** | ~$50 | 10-20% от прибыли |
| **Итого** | **~$200/мес** | Для продакшена |

### Профессиональный (~$2000/мес)

| Компонент | Стоимость | Примечание |
|-----------|-----------|------------|
| **Dedicated Server** | $500 | AMD EPYC, 64GB RAM |
| **Solana RPC (3 ноды)** | $400 | Helius + Alchemy + Triton |
| **Base RPC (2 ноды)** | $200 | Alchemy + QuickNode |
| **Managed DB** | $100 | Timescale Cloud |
| **Jito Tips** | ~$800 | Активная торговля |
| **Итого** | **~$2000/мес** | Макс. производительность |

### Окупаемость

| Сценарий | Прибыль/день | Прибыль/мес | ROI |
|----------|--------------|-------------|-----|
| **Минимальный** | $5-20 | $150-600 | 15-60x |
| **Оптимальный** | $50-200 | $1500-6000 | 7-30x |
| **Профессиональный** | $200-1000 | $6000-30000 | 3-15x |

> ⚠️ **Реалии 2026:** Конкуренция высокая, edge выжат. Ожидайте прибыль в нижнем диапазоне.

---

## 📈 Примеры Запросов

### SQL: Топ возможностей за 24 часа

```sql
SELECT 
    token_symbol,
    COUNT(*) as opportunities,
    AVG(estimated_profit_usd) as avg_profit,
    MAX(spread_net_percent) as max_spread
FROM arbitrage_opportunities
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY token_symbol
ORDER BY avg_profit DESC
LIMIT 10;
```

### SQL: Средняя длительность возможности

```sql
SELECT 
    AVG(lifetime_ms) as avg_lifetime_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY lifetime_ms) as p95_lifetime_ms
FROM arbitrage_opportunities
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

### PromQL: Частота сканирования

```promql
# Сканирований в секунду (5m среднее)
rate(arb_scanner_scans_total[5m])

# По сетям
sum by (network) (rate(arb_scanner_scans_total[5m]))
```

### PromQL: Процент успешных возможностей

```promql
# Возможности со спредом > 0.5%
sum(arb_scanner_spread_percent_bucket{le="+Inf"}) 
- 
sum(arb_scanner_spread_percent_bucket{le="0.5"})
```

### PromQL: 95-й перцентиль прибыли

```promql
histogram_quantile(0.95, rate(arb_scanner_profit_usd_bucket[1h]))
```

---

## 🖼️ Примеры Вывода

### Лог сканера

```
🚀 Starting Arbitrage Scanner v3.0...
✅ Database connected: localhost:5432/arb_scanner
✅ Prometheus metrics server started on port 9090
✅ Solana RPC & Pool Tracker initialized
✅ Base RPC & Pool Tracker initialized
✅ Scanner started
============================================================
💡 Opportunity: SOL | raydium → orca | Spread: 0.58% | Profit: $58.00 | Lifetime: 150ms
💡 Opportunity: ETH | uniswap → aerodrome | Spread: 0.42% | Profit: $42.00 | Lifetime: 230ms
📊 Scans: 30, Duration: 60s, Avg scan time: 485.23ms
```

![Scanner Logs](docs/images/logs-example.png)
*Пример: Лог сканера с найденными арбитражными возможностями*

### Telegram алерт

```
🚀 Arbitrage Opportunity Detected!

🪙 Token: SOL
⏰ Time: 2026-03-07 14:30:00

📊 Route:
  Buy: raydium
  Sell: orca

💰 Prices:
  Buy Price: $150.000000
  Sell Price: $152.000000

📈 Spread:
  Gross: 1.33%
  Net: 0.58%

💵 Estimated Profit: $58.00
⛽ Gas + Tip: $0.15

📉 Slippage: 0.20%
⏱️ Lifetime: 150ms
💧 Liquidity: $100,000
```

![Telegram Alert](docs/images/telegram-alert-example.png)
*Пример: Telegram уведомление о найденной возможности*

### Grafana Дашборд

![Grafana Dashboard](docs/images/grafana-dashboard.png)
*Пример: Grafana дашборд с метриками сканера*

**Ключевые панели:**
- **Total Opportunities** — общее количество найденных возможностей
- **Scan Rate** — частота сканирования (сканов/сек)
- **RPC Latency** — задержка RPC нод в реальном времени
- **Spread Distribution** — распределение спредов (гистограмма)
- **Profit Distribution** — распределение прибыли
- **Opportunities by Token** — возможности по токенам

> 📌 **Совет:** Импортируйте `dashboard/grafana.json` для развёртывания дашборда.

---

## ⚠️ Предупреждения

1. **Не является финансовым советом** — используйте на свой страх и риск
2. **Возможны потери** — проскальзывание, неудачные транзакции, баги
3. **Тестируйте на тестнете** — перед запуском на основных сетях
4. **Следите за лимитами RPC** — бесплатные тарифы ограничены
5. **Безопасность ключей** — никогда не коммитьте `.env` и ключи

---

## 📄 Лицензия

MIT License

```
Copyright (c) 2026 akoffice933-maker

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🤝 Поддержка

- **GitHub Issues**: [Сообщить о проблеме](https://github.com/akoffice933-maker/arb-scanner/issues)
- **Discussions**: [Обсуждения и вопросы](https://github.com/akoffice933-maker/arb-scanner/discussions)

---

## 📊 Звёзды

[![Star History Chart](https://api.star-history.com/svg?repos=akoffice933-maker/arb-scanner&type=Date)](https://star-history.com/#akoffice933-maker/arb-scanner&Date)

---

**Version:** 3.0.0  
**Last Updated:** Март 2026  
**Made with ❤️ by akoffice933-maker**
