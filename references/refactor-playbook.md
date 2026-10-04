# Refactor Playbook

How to clean up large or tangled code **without breaking it**. Adapted from the small-steps,
behavior-preserving discipline in Fowler's *Refactoring* and Feathers' *Working Effectively with
Legacy Code*.

## The one rule

**Refactoring changes structure, not behavior.** Behavior changes and structural changes are
separate patches. If you find yourself "fixing" a bug mid-refactor, stop and do it as a separate
change.

## Step 0 — Establish a safety net (before any edit)

You cannot safely refactor code you cannot verify. Choose the strongest net you can get quickly:

1. **Existing tests** that cover the code — run them and confirm they are green first.
2. **Characterization tests** — if tests are missing, write tests that *freeze current behavior*,
   including behavior that looks wrong. You are capturing what the code does, not what it should
   do. Name them for the behavior, not the implementation.
3. **Snapshot / golden outputs** — for functions with structured or large output, capture the
   current output to a fixture and assert against it.
4. **A manual reproduction** — as a last resort, record exact inputs and observed outputs so you
   can re-check by hand after each step.

If the code is untestable because of hidden dependencies (globals, hard construction, I/O), see
"Dependency breaking" below — you may need a seam before you can test.

## The legacy loop

For code that is expensive to change safely:

1. **Identify the change point** — the smallest place the requested behavior lives.
2. **Check existing protection** — is it covered? If not, characterize.
3. **Find or create a seam** — a place where you can substitute, observe, or intercept without
   editing the whole module.
4. **Break the blocking dependency** — expose the hidden input, injected the collaborator, wrap
   the global, split construction from use.
5. **Make the change** — behavior change now, under the net.
6. **Refactor locally** — with the change protected, clean up the immediate area.
7. **Leave it more testable** than you found it.

## Extract-a-module procedure (the common case)

1. **Pick one seam.** Not the biggest — the smallest boundary that removes the most friction.
2. **Create the target module** with a responsibility docstring.
3. **Move** the code. Keep names; do not redesign at the same time.
4. **Update imports** at every call site.
5. **Run the tests.** Green means the move is behavior-preserving.
6. **Commit** — one structural step. Message: describe the move, not "refactor".
7. **Repeat** for the next seam.

Never move several responsibilities in one commit. If a commit is too large to review locally, it
is too large.

## Dependency breaking (when tests are hard to write)

Blocking dependencies and their usual fixes:

| Blocker | Fix |
|---|---|
| Hard construction of a collaborator (`new Service()` inside) | Inject it via constructor or parameter |
| Global / static state, singletons | Encapsulate behind a parameter or an injectable holder |
| Direct I/O: files, network, DB, clock, randomness | Introduce a boundary (adapter/interface) and inject a fake |
| Constructor does real work | Split construction from use; build a factory |
| Method mixes pure computation with side effects | Extract the pure part first — it is easy to test |

Prefer ordinary object seams (parameters, interfaces) over clever ones. If you add a seam only
for testing (a public-for-test method, a subclass hook, a build trick), note it and remove it once
real structure exists.

## When the repo has no tests

This is the normal case for vibe-coded projects, and exactly why AI refactors break things.

- Do **not** start with a module-wide cleanup.
- Make the **smallest possible structural move**, guarded by a characterization test you add for
  the specific behavior you touch.
- Grow the safety net as you go: each touched behavior gets frozen before you move it.
- Prefer `sprout`/`wrap` style additions (add new code alongside, delegate, then migrate) over
  editing fragile logic in place.
- Keep behavior changes and cleanup in separate commits, even here.

## Stop condition

Stop when:

- the requested change is easy to make and understand;
- the specific friction that blocked it is gone;
- the next cleanup would be **speculative** — adding structure for a case that does not exist yet.

Over-refactoring is its own debt. "Cleaner" is not the same as "different", and a cohesive large
module is not a problem to be solved.

## Anti-patterns

- One giant "refactor everything" commit mixing renames, moves, and logic changes.
- Deleting or loosening a test so a refactor can pass.
- Leaving a test-only seam or wrapper in production code forever.
- Introducing an interface, factory, or pattern for a single implementation.
- Renaming/formatting while the real dependency knot stays untouched.
- "While I'm here" cleanup that expands the blast radius beyond the requested change.
