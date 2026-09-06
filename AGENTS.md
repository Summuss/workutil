## Agent skills

### Issue tracker

Issues and specs live as markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Project docs

- `docs/requirements.md` — what workutil should do and why. No technical details.
- `docs/design.md` — how it's built: architecture, stack, module layout, milestones.

Keep the split: requirements describe observable behavior, design describes implementation. When a change affects both, update both.

## Git workflow

Commit granularity depends on the phase:

- **During `/implement`**: one commit per ticket, made once the whole ticket is done — every acceptance criterion met, tests green, `/code-review` clean. Name the ticket number in the message.
- **All other work** (docs, config, standalone fixes): one commit per logical change, made as you go.
