# Workflow Engine - AI Agent Orchestration System

A minimal yet powerful workflow/graph engine for executing agent workflows, built with Python and FastAPI. This system enables you to define, execute, and monitor multi-step workflows with support for conditional branching and loops.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Sample Workflow: Code Review Agent](#sample-workflow-code-review-agent)
- [Architecture](#architecture)
- [What I Would Improve](#what-i-would-improve)
- [Project Structure](#project-structure)

---

## 🎯 Overview

This workflow engine allows you to:
- **Define workflows as graphs** with nodes (functions) and edges (connections)
- **Execute workflows** with state management and execution tracking
- **Handle complex logic** including conditional branching and loops
- **Monitor execution** with detailed logs and real-time state inspection

Built as part of an AI Engineering Internship assignment, this project demonstrates clean architecture, async programming, and production-ready code structure.

---

## ✨ Features

### Core Engine Capabilities
- ✅ **Node-based workflow execution** - Define workflows as directed graphs
- ✅ **State management** - Shared state flows between nodes
- ✅ **Conditional branching** - Route execution based on state conditions
- ✅ **Loop support** - Repeat nodes until conditions are met
- ✅ **Max iteration safety** - Prevents infinite loops
- ✅ **Tool registry** - Centralized function management
- ✅ **Persistent storage** - SQLite-based graph and run persistence

### API Features
- ✅ **RESTful endpoints** - Create graphs, run workflows, check status
- ✅ **Async operations** - Non-blocking execution with FastAPI
- ✅ **Input validation** - Pydantic models ensure data integrity
- ✅ **Error handling** - Graceful failures with detailed error messages
- ✅ **Auto-generated docs** - Interactive Swagger UI at `/docs`

### Sample Workflow
- ✅ **Code Review Agent** - Analyzes Python code for quality issues
- ✅ **Iterative improvement** - Loops until quality threshold met
- ✅ **Real code analysis** - Complexity, nesting, docstrings, etc.

---

## 🛠 Tech Stack

- **Python 3.10+** - Modern Python with type hints
- **FastAPI** - High-performance async web framework
- **Pydantic** - Data validation and settings management
- **SQLite + aiosqlite** - Async database operations
- **Uvicorn** - ASGI server

---

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or download the project**
```bash
   cd workflow-engine
```

2. **Create virtual environment**
```bash
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Activate (Mac/Linux)
   source venv/bin/activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Verify installation**
```bash
   python -c "import fastapi, pydantic, aiosqlite; print('✅ All dependencies installed')"
```

---

## 🚀 Quick Start

### Start the Server
```bash
python run.py
```

You should see:
```
INFO:     Starting workflow engine...
INFO:     ✅ Storage initialized
✅ Code review tools registered: [...]
INFO:     ✅ Workflow engine ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Access API Documentation

Open your browser and navigate to:
```
http://localhost:8000/docs
```

This opens the interactive Swagger UI where you can test all endpoints.

### Run the Sample Workflow

In a new terminal (keep the server running):
```bash
# Activate venv
venv\Scripts\activate

# Run the code review test
python test_code_review.py
```

This will:
1. Create a Code Review workflow graph
2. Analyze sample Python code
3. Display detected issues and suggestions
4. Show quality scores and iteration counts

---

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. **Create Workflow Graph**
```http
POST /graph/create
```

**Request Body:**
```json
{
  "name": "My Workflow",
  "description": "Description of workflow",
  "nodes": [
    {
      "name": "node1",
      "node_type": "function",
      "tool_name": "my_tool"
    }
  ],
  "edges": [
    {
      "from_node": "node1",
      "to_node": "node2",
      "condition": "state['value'] > 5"
    }
  ],
  "entry_point": "node1"
}
```

**Response:**
```json
{
  "graph_id": "uuid-here",
  "message": "Graph created successfully"
}
```

---

#### 2. **Execute Workflow**
```http
POST /graph/run
```

**Request Body:**
```json
{
  "graph_id": "uuid-here",
  "initial_state": {
    "key": "value"
  }
}
```

**Response:**
```json
{
  "run_id": "uuid-here",
  "status": "completed",
  "final_state": {...},
  "execution_logs": [...],
  "total_execution_time_ms": 150.5,
  "iterations_completed": 2
}
```

---

#### 3. **Get Run State**
```http
GET /graph/state/{run_id}
```

**Response:**
```json
{
  "run_id": "uuid-here",
  "status": "completed",
  "current_node": "final_node",
  "current_state": {...},
  "iterations_completed": 2,
  "started_at": "2024-12-11T10:00:00Z",
  "completed_at": "2024-12-11T10:00:01Z"
}
```

---

#### 4. **List All Graphs**
```http
GET /graph/list
```

---

#### 5. **List Runs for Graph**
```http
GET /graph/runs/{graph_id}?limit=10
```

---

## 🔍 Sample Workflow: Code Review Agent

The included Code Review Agent demonstrates all engine capabilities:

### Workflow Steps

1. **Extract Functions** - Parse Python code and extract function definitions
2. **Check Complexity** - Calculate cyclomatic complexity for each function
3. **Detect Issues** - Find code smells (long functions, deep nesting, etc.)
4. **Suggest Improvements** - Generate actionable suggestions
5. **Calculate Quality** - Compute quality score (0-10)

### Loop Logic

The workflow loops back to step 4 (Suggest Improvements) if:
- Quality score < 8.0
- Iteration count < 5 (safety limit)

### Quality Scoring

**Penalized for:**
- High complexity (>10)
- Long functions (>50 lines)
- Deep nesting (>4 levels)
- Missing docstrings
- Code smells

**Score Range:** 0-10 (threshold: 8.0)

### Example Output
```
📈 Functions Found: 2
  - process_data: 15 lines, complexity 12
  - calculate: 15 lines, complexity 12

⚠️  Issues Detected: 6
  [HIGH] Function 'process_data' has high complexity (12)
  [MEDIUM] Function 'process_data' has deep nesting (5 levels)

💡 Suggestions: 3
  [HIGH] Reduce complexity by extracting nested logic
  [MEDIUM] Flatten nested structures using early returns

🎯 Quality Score: 2.5/10
🔁 Improvement Iterations: 5
```

---

## 🏗 Architecture

### High-Level Design
```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Layer                       │
│  POST /graph/create  |  POST /graph/run  |  GET /state │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Graph Engine                          │
│  • Node traversal                                       │
│  • State management                                     │
│  • Branching & looping                                  │
│  • Execution logging                                    │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────┐          ┌──────────────┐
│ Tool Registry│          │   Storage    │
│  (Singleton) │          │   (SQLite)   │
│              │          │              │
│ • Functions  │          │ • Graphs     │
│ • Tools      │          │ • Runs       │
└──────────────┘          └──────────────┘
```

### Key Components

**1. Models (`app/core/models.py`)**
- Pydantic models for type safety
- GraphDefinition, NodeDefinition, EdgeDefinition
- Run, ExecutionLog, WorkflowState

**2. Tool Registry (`app/core/tool_registry.py`)**
- Singleton pattern
- Manages callable functions
- Decorator-based registration

**3. Graph Engine (`app/core/graph_engine.py`)**
- Core execution logic
- Handles branching with condition evaluation
- Loop detection and max iteration safety
- Async tool execution

**4. Storage (`app/storage/`)**
- Abstract interface + SQLite implementation
- Async database operations
- JSON serialization for complex types

**5. API Routes (`app/api/routes.py`)**
- RESTful endpoints
- Request/response validation
- Error handling

**6. Workflows (`app/workflows/`)**
- Sample workflow implementations
- Tool definitions
- Graph configurations

---

## 🚧 What I Would Improve With More Time

### High Priority
1. **WebSocket Support** - Stream execution logs in real-time
2. **Background Tasks** - Run long workflows asynchronously using Celery/Redis
3. **Authentication** - Add API key authentication for production use
4. **Rate Limiting** - Prevent API abuse
5. **Comprehensive Testing** - Unit tests for all components, integration tests

### Medium Priority
6. **PostgreSQL Support** - Replace SQLite for production deployments
7. **Workflow Visualization** - Generate graph diagrams from definitions
8. **Parallel Execution** - Run independent nodes concurrently
9. **Workflow Versioning** - Track changes to graph definitions
10. **Metrics & Monitoring** - Prometheus/Grafana integration

### Nice to Have
11. **CLI Tool** - Command-line interface for workflow management
12. **Docker Support** - Containerization for easy deployment
13. **Graph Validation** - Detect cycles, unreachable nodes
14. **Conditional Nodes** - Dedicated node type for branching logic
15. **Sub-workflows** - Compose workflows from other workflows


---


## 🤝 Contributing

This is an assignment project, but feedback is welcome! Key areas:
- Code structure and organization
- API design decisions
- Error handling patterns
- Documentation clarity

---
