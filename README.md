# FitFindr

FitFindr is a multi-tool AI agent that helps users discover secondhand clothing items and understand how they can be styled with an existing wardrobe. The agent searches a mock thrift listings dataset, generates outfit recommendations using the user's wardrobe, and creates a shareable social-media-style fit card.

The project demonstrates multi-tool orchestration, state management, error handling, and agent planning using a structured planning loop.

---

## Architecture Overview

```mermaid
flowchart TD
    U[User query] --> P[Planning loop]
    P --> Q[Parse description, size, and max_price]

    S[(Session state)]
    P <--> S
    Q <--> S

    Q --> T1["search_listings(description, size, max_price)"]
    T1 <--> S

    T1 -->|No matches| E1[Set session.error and stop]
    T1 -->|Matches found| R[Store session.search_results]
    R --> I[Select top result as session.selected_item]

    I --> T2["suggest_outfit(session.selected_item, wardrobe)"]
    T2 <--> S

    T2 -->|Empty outfit| E2[Set session.error and stop]
    T2 -->|Valid outfit| O1[Store session.outfit_suggestion]

    O1 --> T3["create_fit_card(session.outfit_suggestion, session.selected_item)"]
    T3 <--> S

    T3 -->|Empty input| E3[Set session.error and stop]
    T3 -->|Success| F[Store session.fit_card]

    F --> U2[Return session to UI]
```

---

## Tool Inventory

### 1. search_listings(description, size, max_price)

**Purpose:**
Retrieves and ranks secondhand clothing listings from the marketplace dataset based on the user's search criteria, budget, and size preferences.

**Inputs:**

* `description (str)` – keywords describing the item the user wants to find
* `size (str | None)` – optional size filter
* `max_price (float | None)` – optional maximum budget

**Output:**

* `list[dict]` – matching listings sorted by relevance score. Each listing contains fields such as `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

---

### 2. suggest_outfit(new_item, wardrobe)

**Purpose:**
Uses an LLM to generate personalized outfit recommendations by combining a selected thrifted item with pieces already present in the user's wardrobe.

**Inputs:**

* `new_item (dict)` – the selected listing returned by `search_listings()`
* `wardrobe (dict)` – the user's wardrobe in the format defined by `wardrobe_schema.json`

**Output:**

* `str` – one or more outfit recommendations. When wardrobe items are available, the response references specific pieces by name. If the wardrobe is empty, the tool returns general styling advice for the selected item.

---

### 3. create_fit_card(outfit, new_item)

**Purpose:**
Uses an LLM to transform an outfit recommendation into a concise social-media-style caption suitable for sharing a completed look.

**Inputs:**

* `outfit (str)` – the outfit recommendation returned by `suggest_outfit()`
* `new_item (dict)` – the selected listing returned by `search_listings()`

**Output:**

* `str` – a 2–4 sentence Instagram/TikTok-style fit card that highlights the thrifted item, reflects the outfit vibe, and naturally incorporates the item name, price, and platform.

---

## Planning Loop

FitFindr follows a **conditional planning loop** rather than calling every tool in a fixed sequence.

1. The agent receives a user query and extracts the values needed for `search_listings()`, including the description, size, and budget.
2. The agent calls `search_listings()` and stores the returned listings in session state.
3. If no listings are found, the agent stores an error message, returns early, and does not call any additional tools.
4. If listings are found, the agent selects the top-ranked result and stores it as `selected_item`.
5. The agent calls `suggest_outfit()` using the selected item and the user's wardrobe.
6. If a valid outfit recommendation is returned, it is stored in session state as `outfit_suggestion`.
7. The agent calls `create_fit_card()` using the outfit recommendation and selected item.
8. The generated fit card is stored in session state and returned to the user.

This workflow allows the agent to change its behavior based on tool outputs. For example, when `search_listings()` returns no results, the workflow stops immediately instead of continuing to later tools with invalid input.

---

## State Management

FitFindr uses a **session dictionary** as the source of truth for a single user interaction. The session stores the original query, parsed search parameters, search results, selected listing, wardrobe information, outfit recommendation, fit card, and any error messages generated during execution.

State is updated as the workflow progresses:

* `session["parsed"]` stores the extracted description, size, and budget values used for searching.
* `session["search_results"]` stores the full list of listings returned by `search_listings()`.
* `session["selected_item"]` stores the top-ranked listing chosen from the search results.
* `session["outfit_suggestion"]` stores the recommendation returned by `suggest_outfit()`.
* `session["fit_card"]` stores the final caption returned by `create_fit_card()`.
* `session["error"]` stores an error message when the workflow cannot continue.

This approach allows information returned by one tool to be passed directly into the next tool without requiring the user to re-enter data. For example, the same `selected_item` produced by `search_listings()` is passed into both `suggest_outfit()` and `create_fit_card()`, while the outfit recommendation generated by `suggest_outfit()` becomes the input to `create_fit_card()`.

---

## Error Handling

Each tool includes explicit error handling so the agent can recover gracefully instead of crashing or continuing with invalid data.

### search_listings()

**Failure mode:** No listings match the user's query.

**Agent behavior:**
`search_listings()` returns an empty list instead of raising an exception. The planning loop detects the empty result, stores an error message in `session["error"]`, and stops before calling any additional tools.

**Example tested:**
I deliberately searched for:

```text
designer ballgown size XXS under $5
```

The tool returned:

```python
[]
```

and the UI displayed:

> No matching listings were found. Try broadening the size filter or increasing your budget.

The workflow stopped before calling `suggest_outfit()` or `create_fit_card()`.

---

### suggest_outfit()

**Failure mode:** The user has an empty wardrobe.

**Agent behavior:**
Instead of failing, the tool generates general styling advice based on the selected item. This allows the workflow to continue and still produce a fit card.

**Example tested:**
I selected **Empty wardrobe (new user)** and searched for:

```text
vintage graphic tee under $50
```

The tool returned general styling advice describing clothing types, shoes, accessories, and outfit vibes without referencing any owned wardrobe items.

The workflow continued successfully and generated a fit card based on the styling recommendation.

---

### create_fit_card()

**Failure mode:** The outfit recommendation is empty or missing.

**Agent behavior:**
The tool returns a descriptive error message string instead of raising an exception.

**Example tested:**

Input:

```python
create_fit_card("", item)
```

Output:

```text
Unable to create a fit card because no outfit suggestion was generated.
```

This prevents the application from crashing and clearly explains what went wrong.

---

## Setup and Running the Project

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure Groq

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_key_here
```

### Run the application

```bash
python app.py
```

Open the URL displayed in the terminal (typically `http://localhost:7860`) and submit a query through the Gradio interface.

### Example Queries

FitFindr supports two wardrobe modes:

* **Example wardrobe** – uses a predefined wardrobe containing tops, bottoms, shoes, outerwear, and accessories.
* **Empty wardrobe (new user)** – simulates a new user who has not added any wardrobe items yet.

#### Example wardrobe

* `vintage graphic tee under $30`
* `90s track jacket in size M`
* `flowy midi skirt under $40`
* `black combat boots size 8`

#### Empty wardrobe (new user)

* `vintage graphic tee under $50`
* `y2k baby tee under $25`

#### Failure-mode test

* `designer ballgown size XXS under $5`
