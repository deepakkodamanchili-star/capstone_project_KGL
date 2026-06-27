# Evaluation datasets

This directory holds sample evaluation data for LeadSift Agent. The datasets are intended for validating the workflow on realistic lead prompts, security cases, and generic out-of-domain questions.

## Quick start

Run the evaluation commands from the project root:

```bash
uv run agents-cli eval generate --dataset tests/eval/datasets/basic-dataset.json
uv run agents-cli eval grade --metrics general_quality --traces ./traces
```

## Dataset contents

- basic-dataset.json: starter examples for lead research and qualification scenarios
- Additional datasets can be added for security, routing, or edge-case behavior

## Dataset format

Each evaluation file uses the standard Agents CLI eval format. A case can be either:

- a single prompt case, or
- a conversation continuation case with prior turns

Example structure:

```json
{
  "eval_cases": [
    {
      "eval_case_id": "lead_research_case",
      "prompt": {
        "role": "user",
        "parts": [{"text": "Jane Doe at Google is the VP of Product Operations."}]
      }
    }
  ]
}
```

## Suggested use cases

- Validate that business leads are researched and scored correctly.
- Confirm that prompt injection attempts are blocked.
- Verify that generic greetings or unrelated questions receive the expected fallback response.

For more details on the evaluation surface, see the Agents CLI documentation.
