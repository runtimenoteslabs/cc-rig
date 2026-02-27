# Cache-Friendly Workflow

Claude Code builds its system around prompt caching. Follow these practices to maximize cache hit rates.

## CLAUDE.md Structure
- Static sections (project identity, commands, guardrails) are at the top.
- Dynamic sections (current context) are at the bottom.
- Everything above the dynamic section is identical across sessions, maximizing cache reuse.

## Do
- Keep CLAUDE.md stable. Avoid frequent edits to the top sections.
- Define all hooks, permissions, and MCP servers upfront. Don't toggle mid-project.
- Use subagents (Task tool) for model escalation instead of switching models mid-session.
- Use `@import` syntax for agent docs (e.g., `@agent_docs/architecture.md`) — auto-loaded at startup, cached efficiently.
- Load team memory files via Read tool on demand, not inline in CLAUDE.md.
- Use CLAUDE.local.md for personal preferences — it's gitignored and won't break cache for teammates.

## Don't
- Don't put memory content directly in CLAUDE.md — it changes every session and breaks cache.
- Don't switch models mid-conversation — this rebuilds the prompt cache.
- Don't conditionally enable/disable hooks during a session.
- Don't connect/disconnect MCP servers during work.
- Don't duplicate agent docs content in CLAUDE.md — use `@import` to reference the source files instead.
