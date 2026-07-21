# Phase 1: Linux Collector Agent Walkthrough & Architecture

The **Linux Collector Agent** is a production-grade, highly secure, non-blocking telemetry collection subsystem. It operates as the foundation of the SRE Platform, capturing host, container, and cluster metrics, normalizing them into structured domain models, and presenting them safely for upstream event parsing, incident grouping, and automated healing analysis.

---

## 1. System Architecture

The system is designed strictly around **Clean Architecture** boundaries. Dependencies only point inwards:

```mermaid
graph TD
    classDef domain fill:#f9f,stroke:#333,stroke-width:2px;
    classDef app fill:#ffb,stroke:#333,stroke-width:2px;
    classDef infra fill:#bbf,stroke:#333,stroke-width:2px;

    %% Domain Layer
    subgraph Domain Layer [Domain Layer - Core Contracts & Rules]
        Collector["Collector (Abstract Base Class)"]:::domain
        MetricType["MetricType (Enum)"]:::domain
        CollectorResult["CollectorResult (Model)"]:::domain
        CommandExecutor["CommandExecutor (Interface)"]:::domain
        CommandValidator["CommandValidator (Interface)"]:::domain
        DomainMetrics["Domain Metrics Models (CPU, Memory, Disk, etc.)"]:::domain
    end

    %% Application Layer
    subgraph Application Layer [Application Layer - Business Logic & Orchestration]
        Registry["CollectorRegistry (Registry Catalog)"]:::app
        Orchestrator["CollectorOrchestrator (Concurrency Engine)"]:::app
        Parsers["Application Parsers (MemoryParser, CPUParser, etc.)"]:::app
    end

    %% Infrastructure Layer
    subgraph Infrastructure Layer [Infrastructure Layer - System Details]
        LinuxExecutor["LinuxCommandExecutor (Subprocesses)"]:::infra
        Collectors["Infrastructure Collectors (MemoryCollector, CPUCollector, etc.)"]:::infra
        LinuxKernel["Linux Kernel / CLI Utilities (sysctl, docker, kubectl, /proc)"]:::infra
    end

    %% Dependency Direction Flows
    Orchestrator --> Registry
    Orchestrator --> Collector
    Collectors -.->|Implements| Collector
    Collectors --> Parsers
    Collectors --> CommandExecutor
    LinuxExecutor -.->|Implements| CommandExecutor
    LinuxExecutor --> CommandValidator
    Parsers --> DomainMetrics
    LinuxExecutor --> LinuxKernel
```

---

## 2. File-by-File Responsibility Directory

### A. The Domain Layer (`src/domain/`)
The Domain layer defines the core contracts, security policies, and schema structures. It is independent of any third-party framework or operating system utility.

| File Path | Responsibility |
| :--- | :--- |
| [collector.py](file:///e:/AI_SRE/src/domain/collectors/collector.py) | Declares the `Collector` abstract class. Forces all concrete collectors to expose a `name`, a `metric_type`, and an async `collect()` routine. |
| [collector_result.py](file:///e:/AI_SRE/src/domain/collectors/collector_result.py) | Holds `CollectorResult` Pydantic schema mapping structured payloads, host metadata, execution lifecycle latency, and parsing errors. |
| [collector_status.py](file:///e:/AI_SRE/src/domain/collectors/collector_status.py) | Declares the collection outcome Enum (`SUCCESS` or `FAILED`). |
| [metric_type.py](file:///e:/AI_SRE/src/domain/collectors/metric_type.py) | Declares type-safe string constants for all collected metrics (`CPU`, `MEMORY`, `DISK`, `NETWORK`, `SERVICE`, `SYSTEM`, `LOG`, `DOCKER`, `KUBERNETES`). |
| [command_executor.py](file:///e:/AI_SRE/src/domain/executor/command_executor.py) | Declares the abstract `CommandExecutor` interface defining asynchronous shell pipelines. |
| [command_result.py](file:///e:/AI_SRE/src/domain/executor/command_result.py) | Wraps stdout, stderr, process exit codes, timeouts, and execution durations. |
| [command_validator.py](file:///e:/AI_SRE/src/domain/executor/command_validator.py) | Enforces the security boundary by validating arguments and verifying that all run commands match an explicit whitelist (e.g., `cat`, `df`, `lsblk`, `systemctl`, `docker`, `kubectl`). |
| [cpu_metrics.py](file:///e:/AI_SRE/src/domain/metrics/cpu_metrics.py) | Normalizes CPU time counters (user, system, idle, iowait). |
| [memory_metrics.py](file:///e:/AI_SRE/src/domain/metrics/memory_metrics.py) | Normalizes total, active, free, cached, and swap usage. |
| [disk_metrics.py](file:///e:/AI_SRE/src/domain/metrics/disk_metrics.py) | Normalizes mount usages, device I/O counters, and remaining space ratios. |
| [network_metrics.py](file:///e:/AI_SRE/src/domain/metrics/network_metrics.py) | Normalizes device RX/TX bytes and error flags. |
| [service_metrics.py](file:///e:/AI_SRE/src/domain/metrics/service_metrics.py) | Normalizes service load configurations and running states. |
| [system_metrics.py](file:///e:/AI_SRE/src/domain/metrics/system_metrics.py) | Normalizes hostname, OS, kernel versions, and shell details. |
| [log_metrics.py](file:///e:/AI_SRE/src/domain/metrics/log_metrics.py) | Normalizes syslog/journalctl events (timestamps, severities, emitting process metadata). |
| [docker_metrics.py](file:///e:/AI_SRE/src/domain/metrics/docker_metrics.py) | Normalizes container definitions, resource consumption states, network models, and volume details. |
| [kubernetes_metrics.py](file:///e:/AI_SRE/src/domain/metrics/kubernetes_metrics.py) | Normalizes cluster version details, namespaces, nodes, pods, deployments, services, and event streams. |

---

### B. The Application Layer (`src/application/`)
This layer handles the orchestration workflow, parallel collector scheduling, and parsing logic. It knows how to translate raw output strings into structured domain models, but it does *not* know how commands are run.

| File Path | Responsibility |
| :--- | :--- |
| [collector_registry.py](file:///e:/AI_SRE/src/application/orchestrator/collector_registry.py) | Manages registration and lifecycle mapping for all active collector classes. |
| [collector_orchestrator.py](file:///e:/AI_SRE/src/application/orchestrator/collector_orchestrator.py) | Schedules and executes registered collectors concurrently using an async tasks pool, logging metrics and managing collector lifecycle. |
| [cpu_parser.py](file:///e:/AI_SRE/src/application/parsers/cpu_parser.py) | Parses `/proc/stat` columns to calculate instantaneous times. |
| [memory_parser.py](file:///e:/AI_SRE/src/application/parsers/memory_parser.py) | Parses `/proc/meminfo` key-value pairs into standard integers. |
| [disk_parser.py](file:///e:/AI_SRE/src/application/parsers/disk_parser.py) | Combines `df` and `lsblk` outputs. |
| [network_parser.py](file:///e:/AI_SRE/src/application/parsers/network_parser.py) | Parses `/proc/net/dev` interface names and bytes count. |
| [service_parser.py](file:///e:/AI_SRE/src/application/parsers/service_parser.py) | Parses `systemctl list-units` rows. |
| [system_parser.py](file:///e:/AI_SRE/src/application/parsers/system_parser.py) | Parses `uname`, `hostname`, and file system releases. |
| [log_parser.py](file:///e:/AI_SRE/src/application/parsers/log_parser.py) | Extracts severity levels and log message structures defensively. |
| [docker_parser.py](file:///e:/AI_SRE/src/application/parsers/docker_parser.py) | Converts memory suffix formats (e.g. `MiB`/`GiB`) to raw bytes and parses inspect JSON models. |
| [kubernetes_parser.py](file:///e:/AI_SRE/src/application/parsers/kubernetes_parser.py) | Parses `kubectl` JSON arrays to extract namespaces, nodes, pods, and deployments. |

---

### C. The Infrastructure Layer (`src/infrastructure/`)
This layer handles concrete system details, subprocess executions, file reads, and OS interactions.

| File Path | Responsibility |
| :--- | :--- |
| [linux_command_executor.py](file:///e:/AI_SRE/src/infrastructure/executor/linux_command_executor.py) | Leverages Python's `asyncio.create_subprocess_exec` to run commands safely. It routes all inputs through the validator to prevent injection attacks and handles execution timeouts. |
| [cpu_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/cpu_collector.py) | Reads `/proc/stat` via `cat` and invokes the `CPUParser`. |
| [memory_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/memory_collector.py) | Reads `/proc/meminfo` via `cat` and invokes the `MemoryParser`. |
| [disk_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/disk_collector.py) | Runs `df` and `lsblk` commands, invoking `DiskParser`. |
| [network_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/network_collector.py) | Reads `/proc/net/dev` and invokes `NetworkParser`. |
| [service_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/service_collector.py) | Runs `systemctl` commands and invokes `ServiceParser`. |
| [system_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/system_collector.py) | Runs `uname`, `hostname` checks and invokes `SystemParser`. |
| [log_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/log_collector.py) | Fallback reads logs from `journalctl`, `/var/log/syslog`, or `/var/log/messages`, invoking `LogParser`. |
| [docker_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/docker_collector.py) | Runs `docker ps`, `inspect`, and `stats`, invoking `DockerParser`. |
| [kubernetes_collector.py](file:///e:/AI_SRE/src/infrastructure/collectors/kubernetes_collector.py) | Runs `kubectl get` commands to fetch cluster resources, invoking `KubernetesParser`. |

---

## 3. Key Design Patterns Implemented

1.  **Dependency Injection (DI)**: Collectors do not instantiate their own executors; they accept a `CommandExecutor` interface at runtime. This allows us to mock the entire OS layer during testing without executing real subprocesses.
2.  **Defensive Parsing**: Parsers wrap execution blocks in try-except statements, handling missing metrics, partial output strings, and different CLI version outputs gracefully.
3.  **Strict Security Whitelist**: The validation layer prevents arbitrary shell injections by strictly validating arguments and blocking characters like `&`, `;`, `\|`, `$`, and command substitutions.

---

## 4. The big picture of how linux collector agent works

### What is the Linux Collector Agent?
The Linux Collector Agent is a read-only telemetry collection service that runs on a Linux machine (or remotely connects to one) and converts everything happening on that machine into a standardized format that the AI SRE Platform can understand.

It does not think.
It does not analyze.
It does not fix.
It simply observes.

Imagine it as the eyes and ears of your AI SRE Platform.

### Why do we need it?
Suppose your production server suddenly becomes slow.
At that moment, the AI SRE Platform cannot magically know what is happening.
First, it needs information such as:
- CPU usage
- Memory usage
- Disk utilization
- Running services
- Network traffic
- Docker containers
- Kubernetes workloads
- System logs

Without this information, no AI can perform Root Cause Analysis (RCA).
So the first job is: Collect everything happening on the server.
That's exactly what the Linux Collector Agent does.

### What does it collect?
Your agent currently collects:
```
Linux Server
│
├── CPU
├── Memory
├── Disk
├── Network
├── Services
├── System Information
├── Logs
├── Docker
└── Kubernetes
```
Every collector specializes in one domain.
For example:
- CPU Collector → CPU statistics
- Memory Collector → RAM statistics
- Docker Collector → Container information
- Kubernetes Collector → Cluster information

### How does it collect information?
It does not read random files directly.
Instead, it uses standard Linux commands.
Examples:
- `free`
- `df`
- `lsblk`
- `systemctl`
- `journalctl`
- `docker ps`
- `docker stats`
- `kubectl get pods`

These commands already know how to retrieve system information. The agent simply executes them safely.

### What happens after executing commands?
Suppose the Memory Collector runs `free -m`. Linux returns something like:
```
              total   used   free
Mem:           7932   2510   4201
Swap:          2047      0   2047
```
Humans can read this, but AI models shouldn't rely on parsing arbitrary terminal text repeatedly.
So your Parser converts it into:
```json
{
    "total_memory_mb": 7932,
    "used_memory_mb": 2510,
    "free_memory_mb": 4201,
    "swap_total_mb": 2047,
    "swap_used_mb": 0
}
```
Now every downstream component receives structured, predictable data.

### Why do we use Parsers?
Because command output is messy (e.g. `journalctl`, `free`, `docker stats`, `kubectl`, `systemctl`). Each command prints data differently.
The parser's job is:
```
Raw Linux Output ──> Structured Python Objects ──> Validated Pydantic Models ──> CollectorResult
```
This makes the rest of the platform independent of command syntax.

### What is a Collector?
Think of a collector as a small robot dedicated to one responsibility.
For example, the Memory Collector:
```
Execute free -m ──> Receive output ──> Call MemoryParser ──> Create MemoryMetrics ──> Return CollectorResult
```
The CPU Collector does the same for CPU, and the Docker Collector does the same for Docker. Every collector follows the same lifecycle.

### What is the Collector Orchestrator?
Instead of manually calling each collector one by one, you have one orchestrator. It simply says: "Run every registered collector."
Conceptually:
```
Collector Orchestrator
  ├── Memory Collector
  ├── CPU Collector
  ├── Disk Collector
  ├── Network Collector
  ├── Service Collector
  ├── System Collector
  ├── Log Collector
  ├── Docker Collector
  └── Kubernetes Collector
```
Since they are asynchronous, they can run concurrently, reducing total collection time.

### What is the final output?
Every collector returns the same structure: `CollectorResult`.
Example:
```json
{
    "collector": "MemoryCollector",
    "status": "SUCCESS",
    "timestamp": "...",
    "hostname": "server01",
    "payload": {
        ...
    }
}
```
The important part is that every collector returns the same envelope, regardless of what it collected.

### What does Phase 1 produce?
After the orchestrator finishes, your AI SRE Platform has a complete snapshot of the server containing CPU, Memory, Disk, Network, Services, Logs, Docker, Kubernetes, and System Information. This is essentially the current state of the machine captured in a structured format.

### What Phase 1 does not do
It does not:
- Detect anomalies
- Explain why CPU is high
- Correlate logs
- Find root causes
- Recommend fixes
- Restart services
- Execute arbitrary command updates
- Heal the system

Those capabilities belong to later phases.

### How does it connect to your test server?
The flow is:
```
Your Laptop
    │
    │ SSH
    ▼
Hostinger Linux Test Server
    │
    ▼
Linux Collector Agent
    │
    ▼
Runs Linux Commands
    │
    ▼
Parses Results
    │
    ▼
CollectorResult Objects
    │
    ▼
AI SRE Platform
```
There are two common deployment approaches:
1. **Agent runs directly on the server** (most common): You copy the Linux Collector Agent to the Hostinger server and run it there. It executes commands locally, which avoids SSH overhead.
2. **Remote execution from your development machine**: Your AI SRE Platform stays on your laptop and connects to the Hostinger server over SSH (using the `LinuxCommandExecutor`/SSH executor). Commands execute remotely, and only the results are returned to your application.

For development and testing, the second approach is perfectly fine.

### The Big Picture
Think of your AI SRE Platform like a human SRE engineer:
```
Phase 1: "I observe."
   │
   ▼
Phase 2: "I organize everything I observed."
   │
   ▼
Phase 3+: "I understand what happened."
   │
   ▼
Later Phases: "I identify the root cause."
   │
   ▼
Final Phases: "I recommend or execute the fix."
```
In one sentence: **The Linux Collector Agent is the telemetry foundation of your AI SRE Platform.** Its sole responsibility is to safely collect raw operational data from Linux systems, normalize it into a consistent structure, and provide that data to the rest of the platform.
