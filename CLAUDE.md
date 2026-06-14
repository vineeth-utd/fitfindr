# CLAUDE.md

## Project Overview

FitFindr is a multi-tool AI agent that helps users find secondhand clothing items and generate outfit suggestions.

The project consists of three required tools:

1. `search_listings(description, size, max_price)`
2. `suggest_outfit(new_item, wardrobe)`
3. `create_fit_card(outfit, new_item)`

These tools are orchestrated through the planning loop implemented in `agent.py`.

## Development Workflow

Always work milestone by milestone.

Before implementing any change:

1. Read only the files required for the current task.
2. Produce an implementation plan.
3. Wait for approval before writing code.

Do not make unrelated changes.

## File Responsibilities

### tools.py

Contains the three required tools.

### agent.py

Contains the planning loop and session state management.

### app.py

Contains the Gradio interface.

### utils/data_loader.py

Provides helper functions for loading listings and wardrobe data. Reuse these helpers instead of creating new data-loading logic.

### planning.md

Source of truth for:

* tool specifications
* planning loop behavior
* state management
* error handling
* architecture

Implementations must follow the specifications in this document.

## Coding Preferences

* Keep implementations simple and readable.
* Prefer straightforward Python over complex abstractions.
* Use descriptive variable names.
* Do not introduce unnecessary classes.
* Do not create new files unless explicitly requested.
* Follow the existing project structure.

## Testing

Implement and test one tool at a time.

Before moving to the next milestone:

* verify happy-path behavior
* verify documented failure modes
* run pytest tests for the affected functionality

## LLM Usage

Use Groq's `llama-3.3-70b-versatile` model for LLM-powered tools.

Follow the behavior defined in `planning.md`:

* `suggest_outfit()` must handle empty wardrobes gracefully.
* `create_fit_card()` must return a descriptive error message when outfit input is empty.

## Prompting Guidelines

When generating outfit suggestions or fit cards:

- Follow the behavior defined in planning.md.
- Do not invent wardrobe items that are not provided.
- Use the selected listing and supplied wardrobe as the primary context.
- Return user-friendly output instead of raw JSON.