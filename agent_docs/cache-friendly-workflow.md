# Cache-Friendly Workflow

Claude Code builds its system around prompt caching. Follow these practices to maximize cache hit rates.

## How Prompt Caching Works

Claude Code assembles each request as: **Tools -> System Prompt (includes CLAUDE.md) -> Messages**. The server hashes this prefix. If it matches a previous request byte-for-byte, cached KV computations are reused at 10% of the base input cost. A single changed byte invalidates everything after the change point.

- Cache reads cost 10% of base input price ($0.30/M on Sonnet vs $3/M uncached).
- Minimum cacheable size: 1024-4096 tokens depending on model.
- TTL: 5 minutes (Pro/API, resets on each hit) or 1 hour (Max, server-controlled).

## 14 Cache-Break Vectors

These actions invalidate the prompt cache (from Claude Code internals):

1. Editing CLAUDE.md (especially top sections)
2. Dependency changes in the project
3. Configuration updates (settings.json, .mcp.json)
4. Memory mutations (if MEMORY.md is inlined)
5. Session state alterations
6. MCP server connect/disconnect
7. Model switches mid-conversation
8. Hook enable/disable toggles
9. Tool schema changes
10. Agent doc modifications (if @imported)
11. Web search toggle
12. Citations toggle
13. Speed setting changes (fast vs standard)
14. Thinking parameter changes

## CLAUDE.md Structure

- Static sections (project identity, commands, guardrails) at the top.
- Dynamic sections (current context) at the bottom.
- Everything above the dynamic section stays identical across sessions, maximizing cache reuse.

## Do

- Keep CLAUDE.md stable. Never edit top sections during a session.
- Define all hooks, permissions, and MCP servers upfront. Don't toggle mid-session.
- Use subagents (Task tool) for model escalation instead of switching models.
- Use `@import` syntax for agent docs (auto-loaded at startup, cached efficiently).
- Load team memory files via Read tool on demand, not inline in CLAUDE.md.
- Use CLAUDE.local.md for personal preferences (gitignored, no team cache breakage).
- Use `--fork-session` for parallel investigations (shares the cache prefix; 3 forks cost 1.55x vs 3.75x for 3 independent sessions).

## Don't

- Don't put memory content directly in CLAUDE.md (changes every session, breaks cache).
- Don't switch models mid-conversation (rebuilds prompt cache entirely).
- Don't conditionally enable/disable hooks during a session.
- Don't connect/disconnect MCP servers during work.
- Don't duplicate agent docs content in CLAUDE.md (use `@import` instead).
- Don't add timestamps, dates, or "last updated" markers in CLAUDE.md static sections.

## Pricing Impact

| Model | Base Input | Cache Read (10x savings) |
|-------|-----------|-------------------------|
| Opus 4.6 | $5.00/M | $0.50/M |
| Sonnet 4.6 | $3.00/M | $0.30/M |
| Haiku 4.5 | $1.00/M | $0.10/M |

A 20-turn session with 100K stable tokens saves approximately 84% on input costs when cache hits are maintained. Poor cache hygiene costs 10x more per turn.
