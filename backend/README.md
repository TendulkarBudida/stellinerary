# Stellinerary — Night Sky Expedition Orchestrator

Stellinerary is an AI-powered "AllTrails for the night sky." It curates celestial events, ranks dark-sky observation sites, checks weather layers, and choreographs a precise, minute-by-minute viewing schedule complete with required gear and narrratives.

This is the backend API, built collaboratively across multiple intelligent agents.

## Stack
- **Backend framework**: FastAPI
- **Math engine**: Skyfield (for Ephemeris)
- **Data validation**: Pydantic
- **Containerization**: Docker
- **Testing**: Pytest

## Architecture Core
Stellinerary operates an orchestrated pipeline mapping directly to user requests:

1. **Curator Agent** (`agents/curator.py`): Finds relevant celestial phenomenons (showers, eclipses, oppositions) filtering for horizon blockages and moon interference metrics.
2. **Location Scout Agent** (`agents/location_scout.py`): Matches the user with the most highly viable dark-sky sites in the target radius.
3. **Weather Agent** (`agents/weather.py`): Gathers 7Timer! astro-weather layering.
4. **Observation Choreographer** (`agents/choreographer.py`): Synchronizes celestial events with site terrain obstructions and clear cloud gaps to form an intelligent observation schedule (incorporating dark adaptation logic).
5. **Gear and Prep** (`agents/gear.py`): Dynamically builds a packing list based on the target events.
6. **Context Storyteller** (`agents/story.py`): Leverages an LLM client to parse rich background narratives on objects in the plan.
7. **Contingency Engine** (`agents/contingency.py` & `scheduler.py`): Runs continuous weather loop checks; safely reschedules operations when clouds roll in.

## Setup & Run Locally

### Approach 1: Virtual Environment
```bash
# Create the environment once (Windows)
py -m venv .venv

# Install and run through the local environment; global Python is not used
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
```
Head to `http://localhost:8000/docs` to test endpoints like `/health` or `/plan`.

### Approach 2: Docker
We provide a lightweight container setup mapping to standard web ports:
```bash
docker build -t stellinerary-backend .
docker run -p 8000:8000 stellinerary-backend
```

## Running Tests
Run the 106-suite test pipeline ensuring 100% interoperability across math, orchestration, and schema validation.
```bash
.venv\\Scripts\\python.exe -m pytest -v
```

## Environment Variables
Copy `.env.example` to `.env` only when you are ready to configure local values:

```bash
copy .env.example .env
```

The application relies on an OpenAI-compatible provider only when attempting the actual Story agent:

```
ENV="development"
LOG_LEVEL="INFO"
LLM_BASE_URL="https://openrouter.ai/api/v1"
LLM_API_KEY=""
LLM_MODEL="openrouter/free"
```

`LLM_API_KEY` is optional for offline/demo operation because the Story agent
falls back to the event description when the provider is unavailable.

`openrouter/free` lets OpenRouter select an available free model. It can still
be temporarily unavailable or rate-limited; use a provider-backed model for
reliable production use.

## Tests and external APIs

The default test command uses mocks and does not contact 7Timer or an LLM:

```bash
.venv\\Scripts\\python.exe -m pytest -q
```

The 7Timer integration test is skipped unless explicitly enabled:

```bash
set RUN_LIVE_API_TESTS=1
.venv\\Scripts\\python.exe -m pytest -m live -q
```
