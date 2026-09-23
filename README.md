# MATIN FORGE Cloud Clone

A fully asynchronous FastAPI service that replicates the core functionality of the **MATIN FORGE (Kuznets)** system. It uses the Groq LLM API to generate step‑by‑step plans, provides a lightweight in‑memory task broker, and can execute shell commands in a safe sandboxed manner.

## Features
- **Planner** – Generates detailed plans via Groq's LLM.
- **Task Broker** – Simple async queue (replaceable with Redis/RabbitMQ).
- **Command Handler** – Executes shell commands with timeout and error handling.
- **Dockerized** – Ready for container deployment.
- **Render Ready** – Includes `render.yaml` for one‑click deployment.
- **CI** – GitHub Actions workflow runs linting and basic tests.

## Quick Start (Local)
```bash
# Clone the repo
git clone https://github.com/your-org/matin-forge-cloud.git
cd matin-forge-cloud

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy from .env.example)
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run the service
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/plan` | Accepts `{ "prompt": "..." }` and returns a generated plan. |
| POST | `/tasks` | Accepts `{ "description": "..." }` and queues a task. |
| GET | `/tasks/next` | Retrieves the next queued task or `null` if none. |
| POST | `/command` | Accepts `{ "command": "..." }` and runs the command safely. |

## Deployment on Render
1. Fork the repository to your GitHub account.
2. In Render, create a **Web Service** and connect the fork.
3. Render will automatically detect `render.yaml`.
4. Add the required environment variables (`GROQ_API_KEY`, optional `GROQ_MODEL`).
5. Deploy!

## CI / CD
The repository includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs:
- **ruff** for linting.
- **pytest** (placeholder – add tests as needed).

## License
MIT © MATIN Team
