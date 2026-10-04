# neatcode

An [Agent Skill](https://agentskills.io/specification) for writing well-structured code and
safely cleaning up large, tangled, or AI-generated files.

Most "clean code" skills are advice. `neatcode` is advice **plus a deterministic tool**: it can
look at your repo, rank the files most worth attention, and help you fix them without changing
behavior.

## What it does

- **Prevention** — a placement protocol that decides where new code belongs *before* it is
  written, so files do not accumulate unrelated responsibilities.
- **Remediation** — a behavior-preserving refactor procedure (pin behavior, extract one seam,
  test, commit, repeat) for files that are already too large or tangled.
- **Measurement** — `audit.py` ranks files by structural cost and detects import cycles, with
  thresholds tuned per project.

## Layout

This repository *is* the skill, so `SKILL.md` sits at the root and the directory name (`neatcode`)
matches the skill `name`, as the specification requires.

```
.
├── SKILL.md                       # triggers + the procedure
├── references/
│   ├── placement-protocol.md
│   ├── refactor-playbook.md
│   ├── comments.md
│   ├── practices.md               # errors, dependencies, injection, concurrency, tests
│   └── adapters/{python,typescript}.md
├── scripts/audit.py               # zero-dependency (Python 3.9+ stdlib)
└── README.md
```

## Install

Because the repo is the skill, install it into a directory named `neatcode`:

```bash
# Personal (all projects)
git clone <this-repo> ~/.commandcode/skills/neatcode

# A specific repo
git clone <this-repo> .commandcode/skills/neatcode
```

Or copy the skill files by hand (drop them into a folder named `neatcode`):

```bash
mkdir -p .commandcode/skills/neatcode
cp -r SKILL.md references scripts .commandcode/skills/neatcode/
```

## Usage

The skill loads automatically when a task matches its description, or explicitly via `/neatcode`.
Run the audit standalone:

```bash
python3 scripts/audit.py .            # ranked worklist
python3 scripts/audit.py . --json     # machine-readable
python3 scripts/audit.py . --init     # re-discover thresholds
```

On first run it writes `.neatcode.json` with thresholds discovered from the repo. Edit that file
to pin values or add exclusions.

The script needs no dependencies. If `lizard`, `cloc`, or `tree-sitter` happen to be installed it
will use them to sharpen its numbers; it never requires them.

## Status

Phase 1: `SKILL.md`, reference playbooks, and `audit.py`. Phase 2 will add a ratchet (fail a build
when a change makes structure worse), seam-finding, a generated module map, hook-based enforcement,
and more language adapters.

## License

MIT
