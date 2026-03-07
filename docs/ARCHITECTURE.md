# Архитектура Arbitrage Scanner v3.0

## Обзор системы

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ARBITRAGE SCANNER v3.0                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   INFLOW      │          │   PROCESS     │          │   OUTFLOW     │
│   (Data In)   │          │  (Business)   │          │   (Data Out)  │
└───────┬───────┘          └───────┬───────┘          └───────┬───────┘
        │                           │                           │
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ • Solana RPC  │          │ • Pool        │          │ • PostgreSQL  │
│ • Base RPC    │          │   Tracker     │          │ • Prometheus  │
│ • Jito        │          │ • Spread      │          │ • Telegram    │
│               │          │   Calculator  │          │ • Grafana     │
│               │          │ • Scanner     │          │               │
└───────────────┘          └───────────────┘          └───────────────┘
```

---

## Компоненты

### 1. Inflow (Входящие данные)

#### Solana RPC Manager
- **Назначение:** Получение данных из сети Solana
- **Реализация:** `infrastructure/rpc_manager.py`
- **Особенности:**
  - Multi-RPC failover (3 ноды)
  - Автоматический выбор ноды с минимальной латентностью
  - Health check каждые 10 секунд
  - Переключение при ошибке

#### Base RPC Manager
- **Назначение:** Получение данных из сети Base
- **Реализация:** `infrastructure/rpc_manager.py`
- **Особенности:**
  - Dual-RPC failover (2 ноды)
  - Аналогично Solana

#### Jito ShredStream
- **Назначение:** Отправка транзакций напрямую валидаторам
- **Реализация:** `infrastructure/shredstream.py`
- **Особенности:**
  - gRPC подключение
  - Bundle отправка
  - Tip management

---

### 2. Process (Бизнес-логика)

#### Pool Tracker
- **Назначение:** Отслеживание состояния пулов ликвидности
- **Реализация:** `core/pool_tracker.py`
- **Классы:**
  - `PoolInfo` — данные пула (адрес, токены, ликвидность, цена, комиссия)
  - `PoolTracker` — управление пулами
- **Алгоритм:**
  1. Инициализация пулов из конфига
  2. Периодическое обновление (каждые 2 сек)
  3. Фильтрация по ликвидности (MIN_LIQUIDITY_USD)
  4. Группировка по токену

```python
# Пример использования
tracker = PoolTracker(network="solana")
await tracker.start(rpc_client)
pools = tracker.get_all_pools()  # List[PoolInfo]
```

#### Spread Calculator
- **Назначение:** Расчёт арбитражного спреда
- **Реализация:** `core/spread_calculator.py`
- **Классы:**
  - `SpreadOpportunity` — данные о возможности
  - `SpreadCalculator` — расчёт спреда
- **Формула:**

```
Gross Spread = (Sell Price - Buy Price) / Buy Price * 100

Net Spread = Gross Spread 
           - Total DEX Fees 
           - Slippage 
           - (Gas + Tip) / Trade Amount * 100

Profit = (Trade Amount * Net Spread / 100) - (Gas + Tip)
```

- **Учитываемые комиссии:**
  - DEX fees (buy + sell)
  - Slippage (зависит от ликвидности)
  - Gas (сетевой fee)
  - Tip (валидатору)

```python
# Пример использования
calculator = SpreadCalculator(sol_price_usd=150.0)
opportunity = calculator.calculate_spread(
    buy_pool=buy_pool_dict,
    sell_pool=sell_pool_dict,
    trade_amount_usd=10000
)
if opportunity and opportunity.spread_net_percent > 0.5:
    print(f"Profitable: ${opportunity.estimated_profit_usd}")
```

#### Arbitrage Scanner
- **Назначение:** Основной цикл сканирования
- **Реализация:** `core/scanner.py`
- **Алгоритм:**
  1. Запуск RPC менеджеров
  2. Запуск Pool Tracker
  3. Цикл сканирования (каждые 0.5 сек)
  4. Сравнение всех пар пулов для каждого токена
  5. Расчёт спреда для каждой пары
  6. Сохранение возможностей в БД
  7. Отправка алертов

```python
# Пример использования
scanner = ArbitrageScanner()
await scanner.start()
# Работает в фоновом режиме
```

---

### 3. Outflow (Исходящие данные)

#### PostgreSQL + TimescaleDB
- **Назначение:** Хранение исторических данных
- **Реализация:** `storage/database.py`, `storage/models.py`
- **Таблицы:**
  - `arbitrage_opportunities` — все найденные возможности
  - `scan_metrics` — метрики сканирования (hypertable)
  - `rpc_status` — история статуса RPC нод

```sql
-- Пример запроса: топ возможностей за 24 часа
SELECT 
    token_symbol,
    COUNT(*) as opportunities,
    AVG(estimated_profit_usd) as avg_profit
FROM arbitrage_opportunities
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY token_symbol
ORDER BY avg_profit DESC;
```

#### Prometheus Metrics
- **Назначение:** Мониторинг производительности
- **Реализация:** `monitoring/metrics.py`
- **Метрики:**
  - Counters: scans_total, opportunities_total, alerts_total
  - Histograms: scan_duration, spread_percent, profit_usd
  - Gauges: rpc_latency, active_pools, current_spread, running

```promql
# Сканирований в секунду
rate(arb_scanner_scans_total[5m])

# 95-й перцентиль прибыли
histogram_quantile(0.95, rate(arb_scanner_profit_usd_bucket[1h]))
```

#### Telegram Alerts
- **Назначение:** Уведомления о значительных возможностях
- **Реализация:** `monitoring/alerts.py`
- **Типы алертов:**
  - Startup notification
  - Opportunity alert (spread > TELEGRAM_ALERT_THRESHOLD)
  - Shutdown notification
  - Error alert

#### Grafana Dashboard
- **Назначение:** Визуализация метрик
- **Реализация:** `dashboard/grafana.json`
- **Панели:**
  - Total Opportunities
  - Max Profit
  - Scanner Running
  - Avg RPC Latency
  - Scan Rate
  - Spread Distribution
  - Profit Distribution

---

## Поток данных

### 1. Запуск

```
main.py
    │
    ▼
ScannerService.start()
    │
    ├──► Database.connect()
    ├──► Metrics.start()
    ├──► Solana RPC Manager.start()
    ├──► Base RPC Manager.start()
    ├──► Solana Pool Tracker.start()
    ├──► Base Pool Tracker.start()
    └──► Scanner._scan_loop()
```

### 2. Цикл сканирования

```
_scan_loop() (каждые 0.5 сек)
    │
    ├──► _scan_network("solana")
    │       │
    │       ├──► Получить все пулы
    │       ├──► Сгруппировать по токену
    │       ├──► Для каждой пары пулов:
    │       │       │
    │       │       ▼
    │       │   calculate_spread()
    │       │       │
    │       │       ▼
    │       │   Если spread > MIN_SPREAD_NET_PERCENT:
    │       │       │
    │       │       ▼
    │       │   _process_opportunity()
    │       │           │
    │       │           ├──► Логирование
    │       │           ├──► Database.save_opportunity()
    │       │           ├──► Metrics.record_opportunity()
    │       │           └──► Если spread > 1%: Metrics.send_alert()
    │
    └──► _scan_network("base") (аналогично)
```

### 3. Обновление пулов

```
PoolTracker._update_loop() (каждые 2 сек)
    │
    ▼
Для каждого пула:
    │
    ▼
_fetch_pool_info(rpc_client)
    │
    ├──► RPC: get_account_info(pool_address)
    ├──► Парсинг данных пула
    ├──► Оценка ликвидности
    ├──► Получение цены
    └──► Возврат PoolInfo
```

### 4. RPC Failover

```
RPCManager.get_client()
    │
    ▼
Если active_node is None или not healthy:
    │
    ▼
_check_all_nodes() (параллельно)
    │
    ▼
_select_best_node()
    │
    ├──► Фильтр: healthy AND latency < 50ms
    ├──► Если есть: выбрать с мин. latency
    └──► Если нет: выбрать первую ноду (fallback)
    │
    ▼
Возврат active_node.client
```

---

## Диаграмма последовательности

```
┌──────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌────────┐
│Scanner│  │RPC Mgr  │  │PoolTracker│  │Calculator│  │Database│  │Metrics │
└───┬──┘  └────┬────┘  └─────┬────┘  └─────┬────┘  └───┬────┘  └───┬────┘
    │          │             │             │           │           │
    │ start()  │             │             │           │           │
    │─────────>│             │             │           │           │
    │          │             │             │           │           │
    │          │ start()     │             │           │           │
    │          │────────────>│             │           │           │
    │          │             │             │           │           │
    │          │             │ fetch()     │           │           │
    │          │────────────>│             │           │           │
    │          │             │             │           │           │
    │          │             │             │           │           │
    │ scan()   │             │             │           │           │
    │─────────>│             │             │           │           │
    │          │             │             │           │           │
    │          │ get_pools() │             │           │           │
    │          │<────────────│             │           │           │
    │          │             │             │           │           │
    │          │             │ calc()      │           │           │
    │          │             │────────────>│           │           │
    │          │             │             │           │           │
    │          │             │ opportunity │           │           │
    │          │             │<────────────│           │           │
    │          │             │             │           │           │
    │          │             │             │ save()    │           │
    │          │             │             │──────────>│           │
    │          │             │             │           │           │
    │          │             │             │           │ record()  │
    │          │             │             │           │──────────>│
    │          │             │             │           │           │
```

---

## Масштабирование

### Вертикальное (Single Node)

```
┌─────────────────────────────────────┐
│  VPS (8 CPU, 16GB RAM, NVMe SSD)   │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Docker Compose               │ │
│  │  ┌─────────┐ ┌─────────────┐  │ │
│  │  │ Scanner │ │ Prometheus  │  │ │
│  │  ├─────────┤ ├─────────────┤  │ │
│  │  │ Grafana │ │ PostgreSQL  │  │ │
│  │  └─────────┘ └─────────────┘  │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Горизонтальное (Multi Node)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Scanner #1   │   │  Scanner #2   │   │  Scanner #3   │
│  (Solana)     │   │  (Base)       │   │  (Both)       │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │   PostgreSQL    │
                  │   (Primary)     │
                  └────────┬────────┘
                           │
                  ┌────────┴────────┐
                  │   PostgreSQL    │
                  │   (Replica)     │
                  └─────────────────┘
```

---

## Безопасность

### Защита ключей

```
.env файл (игнорируется Git)
    │
    ▼
Environment Variables
    │
    ▼
Приложение (не логирует ключи)
```

### Сетевая безопасность

```
┌─────────────────────────────────────────┐
│            Firewall Rules               │
│                                         │
│  Inbound:                               │
│  - 5432 (PostgreSQL) — localhost only   │
│  - 9090 (Prometheus) — trusted IPs      │
│  - 3000 (Grafana) — trusted IPs         │
│                                         │
│  Outbound:                              │
│  - 443 (HTTPS) — RPC endpoints          │
│  - 443 (HTTPS) — Jito                   │
└─────────────────────────────────────────┘
```

---

## Производительность

### Целевые метрики

| Метрика | Цель | Реальность |
|---------|------|------------|
| Scan frequency | 2/sec | ✅ 0.5s интервал |
| RPC latency | < 100ms | ✅ Multi-RPC выбор |
| Scan duration | < 500ms | ✅ ~400-480ms |
| Opportunity lifetime | < 1000ms | ✅ ~150-500ms |
| Database write | < 50ms | ✅ Async + pool |

### Оптимизации

1. **Async I/O** — все RPC запросы асинхронные
2. **Connection Pooling** — пул соединений с БД
3. **Batch Operations** — групповые запросы
4. **Caching** — кэш последних возможностей
5. **Indexing** — индексы на timestamp, token_symbol

---

## Расширение

### Добавление новой сети

1. Создать RPC Manager для сети
2. Добавить Pool Tracker с конфигами пулов
3. Обновить `TARGET_NETWORKS` в settings
4. Добавить метрики для сети

### Добавление нового DEX

1. Добавить пул в `SOLANA_POOLS` или `BASE_POOLS`
2. Указать адрес, токены, комиссию
3. При необходимости: парсер данных пула

### Добавление новой метрики

1. Создать метрику в `monitoring/metrics.py`
2. Обновить `record_*()` метод
3. Добавить панель в Grafana

---

**Version:** 1.0  
**Last Updated:** Март 2026
