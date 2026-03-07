# Contributing to Arbitrage Scanner

Thank you for considering contributing to Arbitrage Scanner! We welcome contributions from the community.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

---

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Keep discussions professional and on-topic

---

## 🚀 Getting Started

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/arb-scanner.git
   cd arb-scanner
   ```
3. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 💻 Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with TimescaleDB
- Docker & Docker Compose (optional)

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt

# Copy environment file
cp .env.example .env
```

---

## 📝 Pull Request Process

1. **Ensure your code passes tests:**
   ```bash
   pytest tests/ -v
   ```

2. **Run linters:**
   ```bash
   flake8 .
   black --check .
   mypy .
   ```

3. **Update documentation** if you change functionality

4. **Add tests** for new features

5. **Squash commits** before submitting:
   ```bash
   git rebase -i HEAD~N
   ```

6. **Submit PR** with clear description of changes

---

## 📏 Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Max line length: 127 characters
- Use type hints (PEP 484)

### Code Organization

```python
# Imports
import asyncio
from typing import Optional, List

# Third-party
from solana.rpc.async_api import AsyncClient

# Local
from config.settings import settings
from core.models import PoolInfo


# Constants
DEFAULT_TIMEOUT = 5.0


# Classes and functions
class ClassName:
    """Docstring for class."""
    
    def method_name(self, arg: str) -> Optional[str]:
        """Docstring for method."""
        pass


# Type aliases
PoolConfig = dict[str, str]
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `pool_tracker` |
| Functions | snake_case | `calculate_spread` |
| Classes | PascalCase | `SpreadCalculator` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT` |
| Private | leading underscore | `_internal_method` |

---

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Specific test file
pytest tests/test_scanner.py -v

# Specific test
pytest tests/test_scanner.py::TestSpreadCalculator::test_calculate_spread -v
```

### Writing Tests

```python
import pytest
from core.spread_calculator import SpreadCalculator


class TestSpreadCalculator:
    """Tests for SpreadCalculator."""

    def setup_method(self):
        """Setup before each test."""
        self.calculator = SpreadCalculator(sol_price_usd=150.0)

    def test_profitable_spread(self):
        """Test calculation of profitable spread."""
        buy_pool = {
            "price_a_per_b": 150.0,
            "fee_percent": 0.25,
            "liquidity_usd": 100000,
        }
        sell_pool = {
            "price_a_per_b": 152.0,
            "fee_percent": 0.30,
            "liquidity_usd": 100000,
        }

        opportunity = self.calculator.calculate_spread(
            buy_pool=buy_pool,
            sell_pool=sell_pool,
            trade_amount_usd=10000,
        )

        assert opportunity is not None
        assert opportunity.estimated_profit_usd > 0
```

---

## 🐛 Reporting Issues

### Bug Report Template

```markdown
**Description:**
Clear description of the bug.

**To Reproduce:**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected behavior:**
What you expected to happen.

**Screenshots:**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.5]
- Docker version: [if applicable]

**Logs:**
```
Paste relevant logs here
```

**Additional context:**
Any other details.
```

---

## 💡 Feature Requests

### Feature Request Template

```markdown
**Problem:**
Is your feature request related to a problem?

**Solution:**
Clear description of what you want to happen.

**Alternatives:**
Alternative solutions you've considered.

**Use case:**
Who will benefit from this feature?

**Additional context:**
Any other details, mockups, etc.
```

---

## 📚 Additional Resources

- [Project README](README.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)

---

## 🎯 Areas Needing Contribution

- [ ] More DEX integrations (Meteora, Cykura)
- [ ] Backtesting framework
- [ ] Web dashboard
- [ ] REST API
- [ ] More unit tests
- [ ] Documentation translations
- [ ] Performance optimizations

---

## 📞 Getting Help

- **GitHub Discussions:** [Ask a question](https://github.com/akoffice933-maker/arb-scanner/discussions)
- **Discord:** [Join our server](LINK)
- **Twitter:** [@yourhandle](https://twitter.com/yourhandle)

---

Thank you for contributing! 🚀
