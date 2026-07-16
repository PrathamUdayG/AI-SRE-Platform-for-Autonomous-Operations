<<<<<<< HEAD
# AI SRE Platform

An AI-driven Site Reliability Engineering platform designed for autonomous infrastructure monitoring, root cause analysis (RCA), and incident remediation.

## Architecture Overview

This project is structured using Clean Architecture and DDD (Domain-Driven Design) principles, organized into four main layers:

- **Domain Layer (`src/domain`)**: Core business logic, entities, value objects, exceptions, and abstract repository/service interfaces. Completely independent of frameworks and outer layers.
- **Application Layer (`src/application`)**: Application use cases, orchestration, and business workflow logic.
- **Infrastructure Layer (`src/infrastructure`)**: Database persistence (PostgreSQL/TimescaleDB), caching (Redis), vector database (Qdrant), external API integrations, SSH host connectors, logging, and dependency injection wiring.
- **Presentation Layer (`src/presentation`)**: Interfaces to the outside world, including a FastAPI REST API, websockets, and dashboard adapters.

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry
- Docker and Docker Compose

### Setup

1. Copy `.env.example` to `.env` and fill in the values:
   ```bash
   cp .env.example .env
   ```
2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```
3. Start local infrastructure services:
   ```bash
   make compose-up
   ```
4. Start the FastAPI development server:
   ```bash
   make run
   ```
=======
# AI-SRE-Platform-for-Autonomous-Operations
>>>>>>> b8c01eabb3ae59faa047b57fe3944d28ef71435e
