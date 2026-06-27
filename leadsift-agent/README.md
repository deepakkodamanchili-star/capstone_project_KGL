# 🚀 LeadSift Agent

LeadSift Agent is an intelligent lead qualification and enrichment workflow built with Google ADK 2.0 and the Model Context Protocol (MCP). It accepts lead submissions, applies security checks, researches company and role context, scores the lead, and routes the result for CRM enrichment or manual review.

## What the project does

- Accepts lead-style prompts and classifies them as valid business requests or generic chatter.
- Redacts sensitive personal data and records security-relevant events.
- Uses MCP-backed tools to gather company and role context.
- Scores leads and routes them through an orchestrated multi-agent workflow.
- Exposes a local playground UI and a FastAPI backend for testing.

## Prerequisites

Before running the project locally, make sure you have:

- Python 3.11 or newer
- uv
- Git
- A Gemini API key from Google AI Studio

## Quick start

1. Clone the repository:
   ```bash
   git clone https://github.com/deepakkodamanchili-star/capstone_project_KGL.git
   cd capstone_project_KGL/leadsift-agent
   ```

2. Create a local environment file:
   ```bash
   cp .env.example .env
   ```
   If there is no .env.example file, create a new .env with:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   GOOGLE_GENAI_USE_VERTEXAI=False
   GEMINI_MODEL=gemini-2.5-flash
   ```

3. Install dependencies:
   ```bash
   make install
   ```

4. Start the playground UI:
   ```bash
   make playground
   ```

5. Open the browser at http://localhost:18081 to interact with the agent.

## Running the app

- Start the playground UI:
  ```bash
  make playground
  ```

- Start the FastAPI backend:
  ```bash
  make run
  ```

- Run the test suite:
  ```bash
  make test
  ```

## Project structure

- app/agent.py: main workflow, agents, routing, and security logic
- app/mcp_server.py: local MCP server implementation
- app/fast_api_app.py: FastAPI entrypoint for the backend
- tests/: unit, integration, and evaluation coverage
- DEMO_SCRIPT.txt: presentation script for the demo

## Demo and evaluation

- Demo script: [DEMO_SCRIPT.txt](DEMO_SCRIPT.txt)
- Evaluation dataset examples: [tests/eval/datasets](tests/eval/datasets)

## Notes

- Keep your .env file private and never commit it to GitHub.
- On Windows, if the playground or backend is locked up, stop existing processes that are using ports 18081 or 8090 before restarting.
- The workflow also handles generic greetings and out-of-domain questions gracefully rather than forcing a lead-scoring action.
