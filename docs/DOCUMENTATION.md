# Documentation: Asana RL Seed Dataset (Enterprise B2B SaaS)

This document covers:

- Section A: Database schema (tables, keys, relationships) + design decisions
- Section B: Seed data methodology (column-by-column strategies, distributions, and consistency rules)

## Section A: Database Schema

### Tables

- organizations
  - organization_id (TEXT, PK)
  - name (TEXT)
  - domain (TEXT)
  - created_at (TIMESTAMP TEXT ISO)

- teams
  - team_id (TEXT, PK)
  - organization_id (TEXT, FK -> organizations.organization_id)
  - name (TEXT)
  - team_type (TEXT)
  - created_at (TIMESTAMP TEXT ISO)

- users
  - user_id (TEXT, PK)
  - organization_id (TEXT, FK -> organizations.organization_id)
  - email (TEXT, unique)
  - full_name (TEXT)
  - title (TEXT)
  - department (TEXT)
  - location (TEXT)
  - role (TEXT)
  - manager_user_id (TEXT, FK -> users.user_id, nullable)
  - hire_date (DATE TEXT ISO)
  - created_at (TIMESTAMP TEXT ISO)
  - deactivated_at (TIMESTAMP TEXT ISO, nullable)

- team_memberships
  - (team_id, user_id) composite PK
  - team_id (TEXT, FK -> teams.team_id)
  - user_id (TEXT, FK -> users.user_id)
  - is_team_admin (INTEGER boolean)
  - joined_at (TIMESTAMP TEXT ISO)
  - left_at (TIMESTAMP TEXT ISO, nullable)

- projects
  - project_id (TEXT, PK)
  - organization_id (TEXT, FK)
  - owner_team_id (TEXT, FK -> teams.team_id)
  - name (TEXT)
  - project_type (TEXT)
  - privacy (TEXT)
  - status (TEXT)
  - start_date (DATE TEXT ISO, nullable)
  - due_date (DATE TEXT ISO, nullable)
  - created_at (TIMESTAMP TEXT ISO)
  - archived_at (TIMESTAMP TEXT ISO, nullable)
  - description (TEXT, nullable)

- sections
  - section_id (TEXT, PK)
  - project_id (TEXT, FK -> projects.project_id)
  - name (TEXT)
  - position (INTEGER)
  - created_at (TIMESTAMP TEXT ISO)

- tasks
  - task_id (TEXT, PK)
  - project_id (TEXT, FK -> projects.project_id)
  - section_id (TEXT, FK -> sections.section_id)
  - name (TEXT)
  - description (TEXT, nullable)
  - creator_user_id (TEXT, FK -> users.user_id)
  - assignee_user_id (TEXT, FK -> users.user_id, nullable)
  - created_at (TIMESTAMP TEXT ISO)
  - updated_at (TIMESTAMP TEXT ISO)
  - start_date (DATE TEXT ISO, nullable)
  - due_date (DATE TEXT ISO, nullable)
  - completed (INTEGER boolean)
  - completed_at (TIMESTAMP TEXT ISO, nullable)

- subtasks
  - subtask_id (TEXT, PK)
  - parent_task_id (TEXT, FK -> tasks.task_id)
  - name (TEXT)
  - description (TEXT, nullable)
  - creator_user_id (TEXT, FK)
  - assignee_user_id (TEXT, FK, nullable)
  - created_at (TIMESTAMP TEXT ISO)
  - updated_at (TIMESTAMP TEXT ISO)
  - due_date (DATE TEXT ISO, nullable)
  - completed (INTEGER boolean)
  - completed_at (TIMESTAMP TEXT ISO, nullable)

- comments
  - comment_id (TEXT, PK)
  - author_user_id (TEXT, FK -> users.user_id)
  - task_id (TEXT, FK -> tasks.task_id, nullable)
  - subtask_id (TEXT, FK -> subtasks.subtask_id, nullable)
  - body (TEXT)
  - created_at (TIMESTAMP TEXT ISO)
  - constraint: exactly one of (task_id, subtask_id) must be non-null

- tags
  - tag_id (TEXT, PK)
  - organization_id (TEXT, FK)
  - name (TEXT)
  - color (TEXT)
  - created_at (TIMESTAMP TEXT ISO)

- task_tags
  - (tag_id, task_id, subtask_id) composite PK
  - task_id (TEXT, FK -> tasks.task_id, nullable)
  - subtask_id (TEXT, FK -> subtasks.subtask_id, nullable)
  - tag_id (TEXT, FK -> tags.tag_id)
  - added_at (TIMESTAMP TEXT ISO)
  - constraint: exactly one of (task_id, subtask_id) must be non-null

- custom_field_definitions
  - custom_field_id (TEXT, PK)
  - organization_id (TEXT, FK)
  - name (TEXT)
  - field_type (TEXT: enum|number|text)
  - enum_options_json (TEXT JSON, nullable)
  - created_at (TIMESTAMP TEXT ISO)

- project_custom_fields
  - (project_id, custom_field_id) composite PK
  - project_id (TEXT, FK)
  - custom_field_id (TEXT, FK)
  - is_required (INTEGER boolean)
  - created_at (TIMESTAMP TEXT ISO)

- custom_field_values
  - custom_field_value_id (TEXT, PK)
  - custom_field_id (TEXT, FK)
  - task_id (TEXT, FK -> tasks.task_id, nullable)
  - subtask_id (TEXT, FK -> subtasks.subtask_id, nullable)
  - value_text (TEXT, nullable)
  - value_number (REAL, nullable)
  - value_enum (TEXT, nullable)
  - created_at (TIMESTAMP TEXT ISO)
  - constraint: exactly one of (task_id, subtask_id) must be non-null

- attachments
  - attachment_id (TEXT, PK)
  - task_id (TEXT, FK -> tasks.task_id, nullable)
  - subtask_id (TEXT, FK -> subtasks.subtask_id, nullable)
  - uploader_user_id (TEXT, FK -> users.user_id)
  - file_name (TEXT)
  - file_type (TEXT)
  - file_size_bytes (INTEGER)
  - created_at (TIMESTAMP TEXT ISO)
  - url (TEXT, nullable)
  - constraint: exactly one of (task_id, subtask_id) must be non-null

### Entity Relationship Diagram

- Source file: `schema.dbml` (import into dbdiagram.io)

### Design decisions

#### Custom fields (vary by project)

- Custom field definitions live in `custom_field_definitions`.
- Project-level enablement is modeled via `project_custom_fields`.
- Values are stored in `custom_field_values` and attach to either a `task` or `subtask` (mutually exclusive constraint).

This mirrors how enterprise Asana usage behaves: global re-usable fields, enabled per project, with sparse/optional values.

#### Task hierarchy (tasks vs subtasks)

- `tasks` are the primary work items and always belong to a project + section.
- `subtasks` are stored in a separate table, linked to `tasks` via `parent_task_id`.

We use separate tables (rather than a self-referential tasks table) because:

- It keeps the relational model simple for RL environments.
- It makes it trivial to enforce that subtasks cannot exist without a parent.

## Section B: Seed Data Methodology

The generator aims to reflect a 5,000–10,000 employee B2B SaaS company with mixed Product/Engineering/Marketing/Operations usage.

### Real-world sources and benchmarks (what informed distributions)

This dataset is synthetic, but *intentionally shaped* by common enterprise project-management patterns:

- **Asana template structures** (sections like To Do / In Progress / Review / Done; campaign workflows; sprint boards).
- **Public issue trackers** (GitHub Issues / PR workflows) for engineering-like task title patterns.
- **Sprint length norms** (2-week sprints are common in Scrum implementations).
- **Asana “Anatomy of Work”** (general productivity planning horizons and collaboration characteristics).

References (for methodology justification; you can cite these in your submission):

- Asana “Anatomy of Work” report hub: https://asana.com/resources/anatomy-of-work
- Scrum Guide (sprint norms / cadence): https://scrumguides.org/
- GitHub Issues (style references): https://docs.github.com/en/issues

### Global distributions and invariants used throughout

- **Org size**: `TARGET_USERS` default 7000 (adjustable to 5000–10000).
- **Unassigned tasks**: ~15% (common in real workspaces where tasks begin unowned).
- **Due dates** (for non-sprint projects):
  - 10% no due date
  - 5% overdue
  - remaining spread across 1w / 1mo / 1–3mo / 3–4mo
- **Task completion rates** vary by project type:
  - sprint: 70–85%
  - bug triage: 60–75%
  - marketing/sales enablement: 55–75%
  - ops initiatives: 45–65%
  - roadmap/ongoing: 40–60%
- **Temporal invariants**:
  - `updated_at >= created_at`
  - If `completed=1` then `completed_at` is populated and >= `created_at`
  - If `completed=0` then `completed_at` is NULL
  - `hire_date <= created_at`

### LLM text generation (Groq) — optional but supported

- Enabled only if `.env` contains:
  - `USE_LLM_TEXT=1`
  - `GROQ_API_KEY=...`
- Prompt templates:
  - `prompts/task_enrich_system.txt`
  - `prompts/task_enrich_user.txt`
- Variety controls:
  - Temperature sampling (default ~0.7)
  - Parameterized prompt context (project name/type/section)
  - Budget via `GROQ_MAX_CALLS` to prevent excessive calls

If Groq is disabled or budget is exhausted, generation falls back to deterministic heuristics.

## Column-by-column seed methodology (by table)

The format below is the authoritative description of how the code generates each column.

### Table: organizations

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| organization_id | TEXT | Generated | UUIDv4 string (`gid()`), simulating Asana-like opaque IDs. |
| name | TEXT | Synthetic corpus | Picked from a curated list of plausible B2B SaaS company names to avoid placeholders. |
| domain | TEXT | Derived | Derived from company name to simulate verified domains; used for email generation. |
| created_at | TEXT | Synthetic | Current timestamp in UTC ISO format. |

### Table: teams

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| team_id | TEXT | Generated | UUIDv4 string. |
| organization_id | TEXT (FK) | Derived | References `organizations.organization_id`. |
| name | TEXT | Synthetic corpus | Department-oriented team naming (“Platform Engineering”, “Demand Generation”, etc.) + some pod/squad expansion to reach `TEAMS_COUNT`. |
| team_type | TEXT | Heuristic | Categorized into `technical` / `go_to_market` / `business_ops` / `cross_functional` based on department-like prefixes. |
| created_at | TEXT | Synthetic | Current UTC ISO timestamp. |

### Table: users

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| user_id | TEXT | Generated | UUIDv4 string. |
| organization_id | TEXT (FK) | Derived | References the single organization. |
| email | TEXT | Faker + de-dup | Generated as `first.last@domain` and forced unique with suffixing to satisfy enterprise email uniqueness constraints. |
| full_name | TEXT | Faker | Faker realistic person names to avoid repeated “User 1” patterns. |
| title | TEXT | Heuristic | Department- and role-aware titles (IC/Manager/Director/Executive) to reflect enterprise structure. |
| department | TEXT | Weighted synthetic | Weighted distribution approximating an enterprise SaaS mix (Engineering-heavy, meaningful GTM/Ops). |
| location | TEXT | Synthetic corpus | Weighted selection from plausible global hubs (India/US/EMEA/APAC). |
| role | TEXT | Heuristic | `executive` created first, then `manager`/`director` (~11%), else `ic`. |
| manager_user_id | TEXT (FK) | Derived | Initially assigned to exec; then updated to department managers where available (hierarchical realism). |
| hire_date | TEXT | Synthetic | Always before `created_at`; log-normal-like tenure distribution with cap. |
| created_at | TEXT | Synthetic | Workday-biased within `HISTORY_DAYS` window (Mon–Wed higher). |
| deactivated_at | TEXT | Synthetic | Small fraction deactivated (~2%) with deactivation after creation and before now. |

### Table: team_memberships

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| team_id | TEXT (FK) | Derived | Primary team inferred from department prefix mapping; secondary membership added ~18% for cross-functional realism. |
| user_id | TEXT (FK) | Derived | References users. |
| is_team_admin | INTEGER | Heuristic | Managers/directors/executives sometimes admins (~22%). |
| joined_at | TEXT | Synthetic | Workday-biased within history window. |
| left_at | TEXT | Derived | If user deactivated, a subset have left_at set to deactivated timestamp. |

### Table: projects

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| project_id | TEXT | Generated | UUIDv4. |
| organization_id | TEXT (FK) | Derived | References organization. |
| owner_team_id | TEXT (FK) | Derived | Random team selection; project type distribution depends on `team_type`. |
| name | TEXT | Synthetic corpus | Template-based names by type (Sprints with week numbers; roadmaps with quarter; campaigns with common GTM terms). |
| project_type | TEXT | Heuristic | One of: `sprint`, `bug_triage`, `product_roadmap`, `marketing_campaign`, `content_calendar`, `ops_initiative`, `sales_enablement`. |
| privacy | TEXT | Heuristic | Mostly public (~86%) to match typical internal workspace visibility; some private. |
| status | TEXT | Heuristic | `active` majority; some `completed`; small `on_hold`. |
| start_date | TEXT | Synthetic | Often set (~85%); else NULL for continuous/ongoing projects. |
| due_date | TEXT | Heuristic | Based on project type (2-week sprint, 4–10 week campaign, 1–4 month roadmap/ops). |
| created_at | TEXT | Synthetic | Workday-biased within history window. |
| archived_at | TEXT | Synthetic/derived | Some completed projects archived later to reflect cleanup behavior. |
| description | TEXT | Template | Short descriptions on ~65% of projects; otherwise NULL. |

### Table: sections

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| section_id | TEXT | Generated | UUIDv4. |
| project_id | TEXT (FK) | Derived | References project. |
| name | TEXT | Template | Section templates per project type (sprint board, bug flow, campaign review flow). |
| position | INTEGER | Derived | Incrementing 0..N per project; extra sections appended with correct ordering. |
| created_at | TEXT | Synthetic | Current UTC ISO. |

### Table: tasks

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| task_id | TEXT | Generated | UUIDv4. |
| project_id | TEXT (FK) | Derived | References owning project. |
| section_id | TEXT (FK) | Derived | Random section within that project. |
| name | TEXT | Heuristics or Groq | By project type: engineering “Component: Verb object (detail)”, marketing “Campaign - deliverable”, ops “Initiative: deliverable”. Optionally refined via Groq. |
| description | TEXT | Templates or Groq | 20% empty, 50% short, 30% richer bullets; optionally refined via Groq. |
| creator_user_id | TEXT (FK) | Derived | Drawn from team membership; biased toward managers/directors for creation patterns. |
| assignee_user_id | TEXT (FK) | Derived | ~15% unassigned; otherwise workload-aware sampling from team members (“power of 3”). |
| created_at | TEXT | Synthetic | Workday-biased; 180-day history window. |
| updated_at | TEXT | Synthetic | Always after created_at; log-normal-ish delay. |
| start_date | TEXT | Synthetic | ~35% set to created_date to mimic “start now” tasks. |
| due_date | TEXT | Heuristic | Sprint tasks cluster at 7–14 days; others follow global due-date distribution with weekday adjustment. |
| completed | INTEGER | Heuristic | Project-type-dependent completion baseline with age-based boost. |
| completed_at | TEXT | Derived | If completed, completion timestamp sampled and clamped within window. |

### Table: subtasks

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| subtask_id | TEXT | Generated | UUIDv4. |
| parent_task_id | TEXT (FK) | Derived | References parent task. |
| name | TEXT | Synthetic corpus | Common execution steps (QA, docs, rollout plan, monitoring). |
| description | TEXT | Sparse template | Most empty; some short clarifications. |
| creator_user_id | TEXT (FK) | Derived | Inherits parent creator (realistic for task breakdown). |
| assignee_user_id | TEXT (FK) | Derived | Often same as parent assignee; sometimes reassigned to simulate delegation. |
| created_at | TEXT | Derived | Anchored to parent updated time. |
| updated_at | TEXT | Synthetic | Always after subtask created_at. |
| due_date | TEXT | Derived | Often inherits parent due date where present. |
| completed | INTEGER | Heuristic | Correlated with parent completion (but not always). |
| completed_at | TEXT | Derived | If completed, after created_at. |

### Table: comments

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| comment_id | TEXT | Generated | UUIDv4. |
| author_user_id | TEXT (FK) | Derived | Random users; realistic comment phrases (dependency, review, validation). |
| task_id / subtask_id | TEXT | Heuristic | Exactly one populated (CHECK constraint). |
| body | TEXT | Synthetic corpus | Realistic collaboration updates and questions; avoids placeholders. |
| created_at | TEXT | Synthetic | Workday-biased. |

### Table: tags

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| tag_id | TEXT | Generated | UUIDv4. |
| organization_id | TEXT (FK) | Derived | References org. |
| name | TEXT | Synthetic corpus | Mix of workstate/metadata tags + quarter/program tags; deduplicated to satisfy unique(org,name). |
| color | TEXT | Synthetic | Chosen from a small palette. |
| created_at | TEXT | Synthetic | Current UTC ISO. |

### Table: task_tags

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| task_id / subtask_id | TEXT | Derived | Tags applied to ~55% of tasks and ~35% of subtasks that exist; 0–2 common, sometimes 3. |
| tag_id | TEXT (FK) | Derived | Random tag selection with plausible “metadata noise”. |
| added_at | TEXT | Derived | Anchored to task/subtask creation. |

### Table: custom_field_definitions

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| custom_field_id | TEXT | Generated | UUIDv4. |
| organization_id | TEXT (FK) | Derived | References org. |
| name | TEXT | Curated set | Enterprise-typical fields: Priority, Status, Story Points, Effort (hours), Channel, Region, Customer Impact, Confidence, Target Release, Owner Group. |
| field_type | TEXT | Curated | `enum`, `number`, `text`. |
| enum_options_json | TEXT | Curated | JSON array for enums (Priority P0–P3 etc.). |
| created_at | TEXT | Synthetic | Current UTC ISO. |

### Table: project_custom_fields

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| project_id | TEXT (FK) | Derived | References project. |
| custom_field_id | TEXT (FK) | Heuristic | Subset enabled per project type (engineering gets Priority/Story Points/Effort; marketing gets Channel/Region; etc.). |
| is_required | INTEGER | Heuristic | Some projects require Status (and rarely others). |
| created_at | TEXT | Synthetic | Current UTC ISO. |

### Table: custom_field_values

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| custom_field_value_id | TEXT | Generated | UUIDv4. |
| custom_field_id | TEXT (FK) | Derived | References definition; generation honors the field’s type. |
| task_id / subtask_id | TEXT | Derived | Currently values attached to tasks; CHECK constraint ensures exclusivity. |
| value_enum / value_number / value_text | Mixed | Heuristic | Type-aware values; includes sparsity so not every task is fully filled (common in real workspaces). |
| created_at | TEXT | Derived | Anchored to task creation. |

### Table: attachments

| Column | Type | Source strategy | Methodology & justification |
| --- | --- | --- | --- |
| attachment_id | TEXT | Generated | UUIDv4. |
| task_id / subtask_id | TEXT | Heuristic | Sparse attachments (~6% of tasks, ~3% of subtasks). |
| uploader_user_id | TEXT (FK) | Derived | Random users. |
| file_name/file_type | TEXT | Synthetic corpus | Common doc types (pdf/docx/xlsx/pptx/png/csv). |
| file_size_bytes | INTEGER | Synthetic | Log-normal-ish distribution to mimic many small files and fewer large files. |
| created_at | TEXT | Synthetic | Workday-biased. |
| url | TEXT | NULL | Left NULL to avoid embedding private URLs. |

## Validation artifact

Run:

```bash
python src/sanity_check.py
```

This writes `output/sanity_report.json` containing row counts and a set of integrity + distribution checks (FK probes, completion timestamp consistency, unassigned rate, due-date sparsity, etc.).
