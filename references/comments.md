# Comment Policy

Comments explain **why**. Code explains **what**. A comment that restates the code is noise that
will drift out of sync and mislead the next reader.

## Rules

1. **Delete restatements.** If a comment says the same thing as the code next to it, remove the
   comment. Improve the names instead.
2. **One responsibility line per module.** Every module opens with a short docstring saying what it
   owns — not a feature list, not a changelog. This is what makes a module map and placement search
   possible.
3. **Document the "why" only:** rationale, constraints, invariants, warnings, workarounds, and
   external contracts. Anything a future reader could not infer from the code.
4. **Prefer clearer code over comments.** A comment that exists only to explain a name is a signal
   to rename, not to document.
5. **Never narrate the diff.** "added this", "now increment", "changed to use X" belong in the
   commit message, not the source.
6. **No banners or decorative blocks.** No ASCII rules, section headers, or multi-paragraph
   headers — they add noise and age badly. Use inline one-line comments only; the module/package
   docstring is the one block comment allowed, and it lives in exactly one place.
7. **A comment that needs a comment is a smell.** If explaining a block takes a paragraph, extract
   a well-named function instead.

## Good vs. bad

Bad — restates the code:

```python
# increment the counter
counter += 1

# loop over the users
for user in users:
    # send the email
    send_email(user)
```

Good — explains why:

```python
# The upstream API counts the first request twice; skip it to avoid double billing.
counter += 1

# Emails must go out in signup order, or the "welcome" template renders before the account
# is marked verified. See INC-482.
for user in sorted(users, key=lambda u: u.created_at):
    send_email(user)
```

Bad — a banner and a narration of mechanics:

```python
# ============================================================
# --- Order processing ---------------------------------------
# ============================================================
# normalize, then hash, then truncate
```

Good — one line that carries the reason the code cannot:

```python
# Order matters: normalizing after hashing would make every fingerprint depend on volatile tokens.
```

Bad — narrates the change:

```ts
// we now use the cache here instead of hitting the db every time
const value = await cache.get(key);
```

Good — states a non-obvious constraint:

```ts
// Cache TTL must exceed the 5s write-consistency window, or readers can observe a torn state.
const value = await cache.get(key);
```

## Module responsibility docstring

Every module should open with one line stating its responsibility. This is the single most
useful comment in a codebase, because it makes "where does this belong?" answerable.

```python
"""Pricing rules for orders: discounts, tax, and rounding. Pure functions, no I/O."""
```

```ts
/** User session tokens: issue, verify, and revoke. Depends on crypto adapter only. */
```

If you cannot write this line, the module probably has more than one responsibility — that is a
placement problem, not a documentation problem.

## Heuristics an agent can apply mechanically

- A comment line whose content is a paraphrase of the next code line → delete it.
- A source file with no top-of-file docstring → add a responsibility line.
- A comment containing "now", "changed", "added", "previously", "TODO: remove" → likely diff
  narration or stale; resolve or delete.
- A block of consecutive comments longer than the code it describes → extract a named function.
- A comment whose only content is a name or a section label (`# Validation`, `# Helpers`) → delete
  it and rely on structure and names.
- Commented-out code → delete it; version control remembers it.

## Not covered by this policy

- Docstrings on public APIs that document parameters, returns, and raised errors are contracts,
  not narration — keep them, and keep them accurate. Keep them as structured docs (JSDoc/`Args:`)
  rather than prose blocks.
- Package/module documentation is legitimate and expected; it just belongs in one place, not
  repeated as banners across the file.
- Generated files and license headers are out of scope.
