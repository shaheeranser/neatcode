# Placement Protocol

The decision procedure for **where new code goes**, run before writing it. This is the
prevention half of neatcode: most god files exist because code was appended to whatever file was
already open. Fixing placement fixes the root cause.

## Why it matters

A module should have **one reason to change**. When a file accumulates unrelated
responsibilities:

- every feature touches it, so every feature risks breaking the others;
- it grows without bound — there is no natural stopping point;
- tests for one responsibility drag in the setup for all of them;
- merge conflicts and review noise multiply.

The cost is paid later, but the decision that causes it takes ten seconds now. That is the whole
point of making the placement decision explicit.

## Procedure

### 1. State the responsibility in one sentence

Write it before touching the editor: *"This code is responsible for \_\_\_."* If you cannot
finish the sentence without "and", you may be about to write two things, which belong in two
places.

### 2. Find the existing home

Search for a module that already owns this responsibility:

- If a `MODULES.md` map exists, read it first — it lists each module's responsibility and public
  API. Do not create a module that already exists.
- Otherwise grep for the domain noun and the operation (e.g. `user`, `invoice`, `parse`, `send`).
  An existing cohesive module beats a new one.

### 3. Match by responsibility, not by convenience

The correct target is the file whose **single responsibility covers the new code** — not:

- the file that is already open in the editor;
- the nearest file by directory;
- the file whose name is closest to the feature, when its responsibility is different.

Ask: *"If I add this here, does this file still have one reason to change?"* If no, keep looking.

### 4. If nothing fits, create a module

A new file with a clear name is almost always better than bloating an unrelated one.

- Name it after the responsibility (`pricing.py`, `TokenVerifier`, `order_totals.ts`) — a noun or
  a verb+noun, concrete and searchable.
- Give it a one-line **responsibility docstring** at the top.
- Keep its imports pointing in one direction (see layering below).

### 5. Global red flags

- Vague bucket names: `utils`, `helpers`, `common`, `misc`, `manager`, `stuff`. These are where
  responsibilities go to hide. Name the actual concept.
- "Put it at the bottom for now" — `for now` never expires.
- The file would gain its 5th+ unrelated responsibility.
- Cross-layer imports: a domain/business module importing the web, CLI, or persistence layer.

## Layering / dependency direction

Dependencies should point **one way**, toward the more stable, more abstract layer:

```
interface / transport  →  application / service  →  domain / model
                                    ↓
                          infrastructure / persistence
```

Concretely, business logic must not depend on framework, HTTP, CLI, or vendor details — those
sit behind a boundary. If adding code forces a lower layer to import a higher one, that is a sign
the code belongs higher up, or that a boundary is missing (add an adapter rather than an upward
import).

## Worked examples

### Example A — new HTTP endpoint

- **Task:** add `PATCH /users/:id`.
- **Bad:** append the route and its SQL to the existing `server.py`, because that is where the app
  is wired. Now routing, validation, and persistence are in one file.
- **Good:** state *"This is an HTTP route for users, so it belongs in `users/routes.py`; the update
  logic belongs in `users/service.py`; the persistence in `users/repository.py`."* Add one small
  handler in `routes.py` that calls the service.

### Example B — a "utility" function

- **Task:** add `format_currency(amount, currency)`.
- **Bad:** drop it in `utils.py` next to unrelated helpers, because that file already exists.
- **Good:** ask what owns it. If it is only used by invoices, put it in `invoices/money.py` with a
  responsibility docstring. If three unrelated areas genuinely need it, create a small
  `formatting/money.py` — but only when there is a real shared concept, not on the first use.

### Example C — new UI component

- **Task:** add a `<UserAvatar>` used by the profile page.
- **Bad:** add it to the existing `components/index.tsx` dump that already exports 40 components.
- **Good:** `components/user-avatar/UserAvatar.tsx`, colocated styles and test, exported from the
  feature that uses it. A shared `components/` barrel is a bucket; feature-local colocation keeps
  the responsibility local.

## Placement one-liner (for your response to the user)

When you decide placement, say it out loud in one sentence before writing:

> "Adding `<thing>` to `<path>` because it owns `<responsibility>."

If the sentence needs an "and", you have found two placements — split them.
