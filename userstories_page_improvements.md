# User Stories Page — Layout Improvements

## Per-story page layout

### Keep (unchanged)

- ID with implementation status tag (e.g. `US-3.2 [implemented]`)
- Title

### Change: move user story and acceptance criteria up

Move the **user story text** ("As a … I want to … so that …") and
**acceptance criteria** to the top of the page, above the diagram and GIF.
Currently they are at the bottom — they should be the first thing visible.

### Diagram and GIF side-by-side

Place the DAG diagram next to the GIF demo, not stacked vertically:

```
|---------------| DAG
|               | DAG
|     GIF       | DAG
|               | DAG
|               | DAG
|---------------| DAG
```

The DAG diagram should have a **transparent background** — no white box
around it, just the graph rendered directly on the page background.

## Navigation: high-level collapsible tree

Show the user story hierarchy as a collapsible tree using the step IDs:

```
A  Step 1a: Account Configuration
  a.0  US-1a.1
  a.1  US-1a.2
  a.2  US-1a.3
B  Step 1b: Category Configuration
  b.0  US-1b.1
  ...
```

**Always unfold (expand) the child leaves**,
so the user can immediately see which stories have demos available.
