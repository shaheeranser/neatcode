---
name: neatcode
description: >-
  Write well-structured code and safely clean up large, tangled, or AI-generated files.
  Decide where new code belongs before writing it, keep modules small and single-purpose,
  write comments that explain why, and refactor in test-guarded steps. Use when adding a
  feature to an existing codebase, splitting a god file, reducing duplication or complexity,
  cleaning up vibe-coded code, or when asked to make code cleaner or improve the architecture.
license: MIT
compatibility: Requires Python 3.9+ for the optional audit script. Optional tools (lizard, cloc, tree-sitter) are used only if already installed.
---

# neatcode

Apply this skill in two situations:

- **Before writing new code** into an existing project — so structure does not rot (Mode A).
- **When a file or module is already large or tangled** — to clean it up safely (Mode B).

Both modes share one stance: **observable behavior is sacred, structure is changed in small
verifiable steps, and no abstractions are added without current evidence.**

## When this applies

Use it when the task involves any of:

- Adding a feature, endpoint, component, or helper to an existing codebase.
- A file that is too long, has too many responsibilities, or is hard to navigate ("god file").
- Reducing duplication, nesting, complexity, or import cycles.
- Cleaning up code that was largely AI-generated or "vibe-coded".
- A request to "make this cleaner", "refactor this", "improve the architecture", or "split this file".

Do **not** use it for: a one-line fix, a change during a code freeze, or documentation-only work.

## Core stance

- **Behavior first.** Never change observable behavior unless the user asked for that change.
  Never disguise a feature change as a refactor.
- **Small steps.** Each structural change stays buildable, testable, and reviewable. Commit after
  each step that passes tests.
- **Measure, then judge.** Line count is a proxy. A cohesive 600-line file can be better than six
  tangled 100-line files. Use metrics to *find candidates*, then decide with cohesion signals.
- **Deep modules, not just small files.** Prefer a simple interface hiding real complexity over
  splitting a file into pass-through fragments.
- **No speculative abstraction.** Generalize only when a third case exists. Delete unused
  indirection and compatibility shims rather than adding layers "just in case".
- **Smallest change that works.** Make the change the task requires and no more; do not broaden it
  to make nearby code look consistent.
- **Surface decisions, do not guess.** If the work needs a decision the request or spec does not
  make, ask — or state the assumption explicitly. Never resolve an open question silently.
- **Leave the touched area cleaner** within the scope of the requested change — not the whole
  codebase at once.

## Mode A — Placement protocol (before writing new code)

Run this **before** creating code. The point is to stop appending to whatever file happens to be
open, which is the root cause of god files.

1. **Name the responsibility.** In one sentence, state what the new code is responsible for.
2. **Find the existing home.** Search the project for a module that already owns this
   responsibility (use the module map if one exists — see Mode B step 0). Prefer an existing
   cohesive module over creating a new one.
3. **Match by responsibility, not convenience.** The right file is the one whose single
   responsibility covers the new code — not the file that is already open, or the nearest.
4. **If nothing fits, create a new module** with a clear name and a one-line responsibility
   docstring at the top. New file beats bloating an unrelated one. A module earns its existence by
   owning a boundary, not by reducing a line count.
5. **State your decision** before writing: "Adding the X handler to `<path>` because it owns Y."
   If you cannot state it in one sentence, the placement is wrong.

Red flags that mean you are about to add structural rot:

- The target file would gain its 5th, 6th, … unrelated responsibility.
- You are about to append "at the bottom" or "for now".
- The new code imports across layers it should not (e.g. a domain module importing the web layer).
- The name for the new module would be a vague bucket: `utils`, `helpers`, `common`, `misc`.

Full decision procedure and worked examples: [references/placement-protocol.md](references/placement-protocol.md).

## Mode B — Cleanup / refactor (large or tangled code)

Work one step at a time. **Never rewrite a large file in a single pass.**

0. **Get the lay of the land.** If a module map (`MODULES.md`) exists, read it to find existing
   homes for code. Otherwise list the files and their responsibilities.
1. **Pin behavior first.** Before editing, establish a safety net: run existing tests, or — when
   they are missing or weak — write *characterization tests* or capture snapshot outputs that
   freeze current behavior. Treat untested code as legacy code.
2. **Find one seam.** Pick the single smallest boundary you can extract or reshape that reduces
   the most friction. Do not refactor every smell you can see.
3. **Extract one module.** Move the code, keep external behavior identical, update imports.
4. **Run the tests.** They must pass with no behavior change. If they fail, fix forward or revert
   the step — do not "adjust" the test to match new behavior.
5. **Commit.** One structural step per commit, with a short labelled message (`refactor: ...`).
   The tree must build and tests must pass at each commit. Keep refactoring separate from any
   behavior change, and leave the user's existing worktree changes intact.
6. **Repeat** until the requested change is easy and the blocking friction is gone. **Stop** before
   cleanup turns speculative.

When the repo has no tests at all: make the smallest structural move, and add characterization
tests for the behavior you are touching as you go — see the playbook.

Full procedure, including dependency-breaking and the no-tests case:
[references/refactor-playbook.md](references/refactor-playbook.md).

## Measuring structure

Run the audit to get a ranked worklist of the files most worth attention:

```bash
python3 scripts/audit.py .            # human-readable ranked worklist
python3 scripts/audit.py . --json     # machine-readable, for scripting
python3 scripts/audit.py . --top 10   # just the worst 10
```

On first run it writes a `.neatcode.json` config with thresholds discovered from the repo, so
the judgement is relative to *this* project. Edit that file to pin thresholds or exclusions.

**Treat the output as a starting point for judgement, not a verdict.** A file ranked high
because it is long may be a single cohesive responsibility and fine to leave; a shorter file
that mixes three responsibilities and sits in an import cycle is usually the better target.

## Comments policy

- Comments explain **why**, not **what**. If a comment restates the adjacent code, delete the
  comment and improve the names instead. A comment that only explains a name is a signal to rename.
- Every module starts with a one-line responsibility docstring: what it owns, not how it works.
- Keep comments for rationale, constraints, warnings, and external contracts (e.g. "workaround
  for <vendor bug>", "must run before X because Y").
- Never narrate the diff ("added this", "now we increment") — that belongs in the commit message.
- No banners or decorative blocks — no ASCII rules, section headers, or multi-paragraph headers.
  Inline one-line comments only; the module docstring is the one block comment allowed, and it
  lives in exactly one place.

Details and examples: [references/comments.md](references/comments.md).

## Cross-cutting practices

These apply regardless of language; details and examples in
[references/practices.md](references/practices.md).

- **Handle errors honestly.** Wrap with context and never discard the original; when several
  independent things can fail, report them together rather than failing on the first. Expected bad
  input is an error to handle, not a crash.
- **Standard library first.** Add a dependency only for something the standard library genuinely
  cannot do, and record why.
- **Inject what you depend on.** Take collaborators — clients, clocks, writers, config — as
  parameters so behavior is testable. Do not reach for globals, singletons, or ambient I/O inside
  logic.
- **Make uncertainty visible.** When something cannot be resolved confidently, preserve the input
  and emit a warning or diagnostic instead of silently dropping data or guessing.
- **One representation.** Do not keep two forms of the same data and reconstruct meaning from the
  weaker one; carry the richest structured form through the system.
- **Concurrency has owners.** Bound every queue and channel, guard shared mutable state, and give
  every goroutine/thread an owner that waits for it.
- **Tests are part of the design.** Write them with the code, keep them deterministic and offline,
  and prefer golden files for anything that parses or renders text.

## Language adapters

Load the adapter for the language you are working in; it gives idiomatic layouts and the
thresholds that fit that ecosystem.

- Python: [references/adapters/python.md](references/adapters/python.md)
- TypeScript / JavaScript: [references/adapters/typescript.md](references/adapters/typescript.md)

## Do not

- Rewrite a whole module or "while I'm here" clean up unrelated code.
- Change behavior silently, or refactor without a safety net when the code is risky.
- Introduce an abstraction, pattern, or interface to serve a hypothetical future case.
- Split a cohesive file into fragments purely to satisfy a line count.
- Delete or weaken a failing test to make a refactor "pass".
- Leave a temporary seam or wrapper behind after it has served its purpose.
- Clobber the user's existing uncommitted changes in the worktree.
- Leave dead code, commented-out code, or compatibility shims behind instead of deleting them.
- Commit generated or derived artifacts (build output, generated files, local reports).

## Enforcement (optional)

The skill teaches the procedure; a script can enforce the outcome. The audit can run as a
pre-commit check or a post-edit hook so that structural regressions surface back to the agent as
feedback rather than as advice that gets skipped. See the design doc for hook wiring (phase 2).

## Worked example

**Prevention.** Task: "add a `PATCH /users/:id` endpoint." Instead of appending to the existing
large `server.py`, state: *"Adding this to `users/routes.py` because it owns user HTTP routes."*
Add the route there, delegate to `users/service.py` for logic, and keep persistence in
`users/repository.py`. If `server.py` is already a god file, do not add to it.

**Remediation.** Task: "`orders.py` is 900 lines and hard to change." Add a characterization test
that freezes current order-total behavior, extract the pricing rules into `orders/pricing.py`,
run tests (green), commit; then extract validation into `orders/validation.py`, run, commit.
Two small commits, behavior unchanged — not one 900-line rewrite.
