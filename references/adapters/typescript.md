# TypeScript / JavaScript Adapter

Idiomatic layout, thresholds, and notes for TypeScript and JavaScript projects.

## Typical layouts

**React app / frontend:**

```
src/
├── features/<feature>/
│   ├── components/     # feature-local components; not a global components/ dump
│   ├── hooks/          # useX hooks for this feature
│   ├── api.ts          # data access for this feature
│   └── types.ts
├── lib/                # genuinely shared, framework-agnostic helpers
└── app/                # routing / composition root only
```

**Node service (Nest/Fastify/Express-style):**

```
src/
├── main.ts            # bootstrap + wiring only
├── <domain>/
│   ├── routes.ts      # HTTP: parse + validate input, call service, shape output
│   ├── service.ts     # business logic; no framework imports
│   ├── repository.ts  # data access
│   └── types.ts
└── shared/            # config, adapters
```

Dependency direction: `routes → service → repository`. Domain code must not import Express/Nest
or the ORM directly — keep those at the boundary.

## Thresholds

Defaults from `.neatcode.json`, tuned for TS/JS:

| Metric | Threshold | Notes |
|---|---|---|
| File length (code lines) | 400 | JSX/TSX often runs longer per concept; judge by responsibility |
| Function length | 50 | Very long functions are usually a component + logic mixed together |
| Cyclomatic complexity | 10 | Per function |
| Nesting depth | 4 | Prefer early returns / guard clauses over nested `if` |
| Import cycles | 0 | Common in barrels; see below |

## TS/JS-specific signals

- **Barrel files (`index.ts`) re-exporting everything** → these create import cycles and hide
  dependencies. Prefer direct imports; keep a barrel only for a package's public surface.
- **`utils.ts` / `helpers.ts` mega-file** → split by concept (`money.ts`, `dates.ts`, `strings.ts`).
- **God component**: a single `.tsx` doing data fetching, state, layout, and business rules →
  split into a container/hook (`useX`) + presentational component; move rules to plain functions.
- **`any` proliferating** to quiet types during a change → a sign the boundary is unclear; model
  the type instead of widening it, and avoid non-null assertions (`!`) to silence the checker.
- **Circular imports** between feature folders → extract the shared piece into `lib/` (a lower
  layer both can depend on) rather than importing sideways.

## Design notes

- **Inject collaborators.** Pass clients, clocks, and fetch implementations in (or take them from
  context) so tests can substitute fakes; avoid reaching for global `fetch`, `Date.now()`, or
  `process.env` inside logic.
- **Validate at the boundary.** Parse and validate external input (zod/schema) where it enters;
  trust validated types inward rather than re-checking everywhere.
- **Throw with context**, or return a typed result; do not swallow errors in empty `catch` blocks.
- **Prefer `unknown` over `any`** and narrow explicitly; prefer named exports over default exports
  (they rename and tree-shake more predictably and make placement easier to reason about).
- **Standard library first.** For a small utility, a local function beats a dependency; justify
  anything you add.

## Refactor notes

- Extract one module or component at a time; run the typecheck (`tsc --noEmit`) and tests after each
  move. A green typecheck is part of the safety net.
- Keep React components presentational where possible; move effects and data access into hooks.
- For characterization tests, snapshot the rendered output or the function return with the project's
  runner (Vitest/Jest); name tests for behavior, not implementation.
- Colocate tests next to the code (`Component.test.tsx`) so a move carries its safety net with it.
