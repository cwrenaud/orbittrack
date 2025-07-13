# OrbitTrack

## NOT YET A PYPI LIBRARY

[![Python CI](https://github.com/cwrenaud/orbittrack/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/orbittrack/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/orbittrack.svg)](https://badge.fury.io/py/orbittrack)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

Python library for interacting with the [Space-Track API](https://www.space-track.org/) to retrieve orbital data for satellites and space objects.

## Features

- Modern, type-annotated Python API (requires Python 3.12+)
- Both synchronous and asynchronous clients
- Automatic authentication management
- Configurable rate limiting with various storage backends
- Comprehensive error handling

## Installation

```bash
pip install orbittrack
```

## Quick Start

### Synchronous Usage

```python
from orbittrack.spacetrack import SpaceTrack

# Create a client
client = SpaceTrack(username="your_username", password="your_password")

# Get GP data for a satellite (ISS = 25544)
gp_data = client.gp("25544")
print(f"Satellite name: {gp_data.OBJECT_NAME}")
print(f"Epoch: {gp_data.EPOCH}")

# Get historical data for a date range
history = client.gp_history("25544", "2023-01-01", "2023-01-31")

# Using a context manager (handles login/logout automatically)
with SpaceTrack(username="your_username", password="your_password") as st:
    data = st.gp("25544")
```

### Asynchronous Usage

```python
import asyncio
from orbittrack.spacetrack.aio import AsyncSpaceTrack

async def main():
    # Create an async client
    client = AsyncSpaceTrack(username="your_username", password="your_password")

    # Get GP data for a satellite (ISS = 25544)
    gp_data = await client.gp("25544")
    print(f"Satellite name: {gp_data.OBJECT_NAME}")
    print(f"Epoch: {gp_data.EPOCH}")

    # Get historical data for a date range
    history = await client.gp_history("25544", "2023-01-01", "2023-01-31")

    # Don't forget to close the client
    await client.close()

    # Using a context manager (handles login/logout automatically)
    async with AsyncSpaceTrack(username="your_username", password="your_password") as st:
        data = await st.gp("25544")

# Run the async function
asyncio.run(main())
```

## Rate Limiting

OrbitTrack provides configurable rate limiting to respect Space-Track's API limitations:

```python
from orbittrack.spacetrack import SpaceTrack
from limits.storage import RedisStorage

client = SpaceTrack(username="your_username", password="your_password")

# Configure rate limits
client.set_minute_rate_limit("20/minute")
client.set_hourly_rate_limit("200/hour")

# Use Redis for distributed rate limiting
redis_storage = RedisStorage("redis://localhost:6379")
client.set_ratelimit_storage(redis_storage)
```

## Advanced Configuration

OrbitTrack supports various rate limiting strategies and storage backends:

```python
from orbittrack.spacetrack.aio import AsyncSpaceTrack
from limits.aio.storage import RedisStorage as AsyncRedisStorage
from limits.aio.strategies import SlidingWindowCounterRateLimiter as AsyncSlidingWindowRateLimiter

# Create async client
client = AsyncSpaceTrack(username="your_username", password="your_password")

# Configure Redis storage
redis_storage = AsyncRedisStorage("redis://localhost:6379")
client.set_ratelimit_storage(redis_storage)

# Configure rate limiter strategy
rate_limiter = AsyncSlidingWindowRateLimiter(redis_storage)
client.set_ratelimiter(rate_limiter)
```

## Development

### Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
pytest
```

Or with coverage:

```bash
pytest --cov=orbittrack
```

## License

MIT

## Credits

Developed by Calvin Renaud
