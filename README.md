<div align="center">

# ⚡ AioFast

### The Async-First Python Framework Inspired

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Typing: strict](https://img.shields.io/badge/typing-strict-green.svg)](https://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-green.svg)]()

**AioFast** is a powerful async-first Python framework.
It combines the best architectural patterns with the power of Python's asyncio.

[Documentation](#-documentation) •
[Quick Start](#-quick-start) •
[Examples](#-examples) •
[Contributing](#-contributing)

---

### 🌟 Why AioFast?

*"elegance meets Python's power"*

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🏗️ Architecture
- **IoC Container** with automatic DI
- **Service Providers** for modularity
- **Bootstrap Pipeline** with phases
- **Middleware** system with parameters
- **Facades** for convenient access

</td>
<td width="50%">

### 🚀 Performance
- **Async-first** — everything is asynchronous
- **Container** integration for DI scopes
- **Rate Limiting** out of the box
- **Caching** with Redis/Memory backends
- **Connection pooling** for databases

</td>
</tr>
<tr>
<td>

### 🌐 Multi-Platform
- **HTTP** — Litestar/FastAPI support
- **Telegram** — Aiogram 3.x integration
- **CLI** — Typer + Rich console
- **Workers** — Background job processing
- **WebSocket** — Real-time support

</td>
<td>

### 🛠️ Developer Experience
- **Artisan CLI** — Code generation
- **Hot Reload** in development
- **Full typing** — IDE autocompletion
- **pytest** — Testing out of the box
- **Pydantic** — Validation & settings

</td>
</tr>
</table>

---

## 📦 Installation

```bash
pip install aiofast
```

Or with Poetry (recommended):

```bash
poetry add aiofast
```

Or with uv:

```
uv add aiofast
```

Requirements

- Python 3.11+
- asyncio support

Optional Dependencies

```
# For PostgreSQL
pip install aiofast[postgres]

# For Redis
pip install aiofast[redis]

# For Telegram
pip install aiofast[telegram]

# Everything
pip install aiofast[full]
```

## 🚀 Quick Start

Create New Project


```
# Create a new project
aiofast new my-project

# Navigate to directory
cd my-project

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Generate application key
python artisan.py key:generate

# Run the application
python artisan.py serve
```


## 🤝 Contributing
We welcome contributions! Please see our Contributing Guide for details.

Development Setup
```
# Clone the repository
git clone https://github.com/AIAnsar1/aiofast.git
cd aiofast

# Install dependencies
poetry install --with dev

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run type checking
mypy aiofast

# Run linting
ruff check aiofast
black --check aiofast
```

## 📄 License
AioFast is open-sourced software licensed under the MIT license.


<div align="center">

## ⭐ Star History
If you find AioFast useful, please consider giving it a star! ⭐

Made with ❤️ and Python
</div> ```









