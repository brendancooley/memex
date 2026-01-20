# Memex

A second brain you talk to like your first.

## The Problem

Calendars, todo lists, email, contacts—these tools have no concept of *you*. They're slots and fields. Your calendar knows you have a preschool tour on Thursday but can't connect it to the notes from last week's visit, the questions you still have, or the gut feeling you had walking through the outdoor classroom. Your contacts app has your college roommate's phone number but doesn't know it's been four months since you talked.

The tools are shallow because life is deep. People, relationships, goals, projects, decisions—these are richly connected. A preschool search isn't a todo item; it's a thread that weaves through visits, conversations, observations, and tradeoffs.

What you need is a **second brain**—not a filing cabinet, but something that actually models your life.

## The Model

Memex is built on two pillars:

**A structured database** for things that have shape: people, events, todos, books, places. Entities with properties and relationships between them. Queryable—"who haven't I talked to in three months?" returns an answer, not a fuzzy search.

**An unstructured scratchpad** for things that don't: exploratory thinking, research threads, half-formed ideas. Markdown files that link to each other, weaving a web of thought.

**An LLM as the interface.** You talk; it files. On input, the agent parses natural language into structured operations. On output, it queries the database and synthesizes human-readable responses. No forms, no folders, no deciding where things go.

The key insight: **writes are casual, reads are synthesized.** You jot fragments as they come. When you need to make a decision or show up somewhere prepared, the system weaves those fragments into context.

## An Example

You're searching for a preschool. Over a few weeks:

```
> We should start looking at preschools for Oliver.
  Started a preschool search doc. I'll track everything there.

> Touring Bright Horizons Thursday at 10am
  Added to calendar. Created Bright Horizons as a school.

> Back from Bright Horizons. Nice outdoor classroom, but felt corporate.
  Class sizes 15:2. $2,800/mo.
  Got it. Updated Bright Horizons with cost and ratio. Added your
  impressions to the preschool search.

> Sarah mentioned her kids went to Community Cooperative—she loved it
  Noted in the preschool search. Linked to Sarah.

> Do we know anyone else with kids at Community Coop?
  Jake's daughter started there last fall.
```

Each input took seconds. No schema to design, no forms to fill.

A month later, you've toured four schools:

```
> Help me think through the preschool decision

Here's what you've captured:

Bright Horizons
  Visited Jan 8. $2,800/mo, 15:2 ratio.
  "Nice outdoor classroom, felt corporate."

Community Cooperative
  Visited Jan 14. $1,900/mo, 8:2 ratio.
  "Very warm, small classes, parents volunteer 2x/month."
  Sarah's kids went here. Jake's daughter just started.

[... two more schools ...]

You mention "teacher ratio" four times and "outdoor space" three.
You seemed most enthusiastic after Community Coop.
Jake said pickup is easy and his daughter loves her teachers.

What's weighing on you?
```

The todo list said "find preschool." Memex helped you decide.

## Two Kinds of Thinking

Some things want structure. People have names, birthdays, relationships. Events have dates and locations. These belong in a database—queryable, sortable, filterable.

Some things resist structure. A career deliberation. A research thread. The slow accumulation of observations about a friendship. These belong in a scratchpad—freeform, interconnected, evolving.

| Database | Scratchpad |
|----------|------------|
| Entities with typed properties | Markdown files with wikilinks |
| SQL queries | Semantic search |
| "List todos due this week" | "Help me think through X" |
| Structured, queryable | Exploratory, navigable |

The two pillars reference each other. A scratchpad document about your preschool search mentions Sarah and Jake—the agent resolves these to Person entities when synthesizing. A Person entity links to the conversations and documents where they appear.

## The Schema Grows With You

The database starts empty. You don't configure entity types upfront—they emerge from what you actually track.

The first time you mention a person, the agent proposes a Person table. The first time you log a book rating, it proposes a Book table. When you mention someone's birthday, it adds a column. The schema evolves continuously, through conversation, with your approval for structural changes.

This is the opposite of Notion, where you design the database before you use it. Memex's schema is *discovered*, not designed.

## The Philosophy

Your primary brain is for presence. Your second brain is for context.

The goal isn't to capture everything—it's to capture enough that you can walk into a meeting, a difficult conversation, a big decision, with the relevant threads already loaded. The agent remembers so you don't have to. It connects so you can show up prepared.

Memex is not a productivity system. It's a way to be less productive at remembering so you can be more present everywhere else.

## Installation

```bash
uv pip install memex
```

## Development

```bash
# Clone the repository
git clone https://github.com/brendancooley/memex.git
cd memex

# Install dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
```
