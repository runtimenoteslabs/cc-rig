# Saving Tokens with cc-rig

Claude Code uses prompt caching to avoid reprocessing the system prompt, CLAUDE.md and tool definitions on every turn. When the cache hits, input tokens cost 10% of the uncached price. When it misses, you pay full price. Over a day of coding, the difference is 5-10x in token spend.

## How prompt caching works

Every Claude Code request is assembled as a prefix:

```
Tools (~5K tokens) -> System Prompt (includes CLAUDE.md) -> Messages
```

The server hashes this prefix. If it matches a previous request byte-for-byte, cached KV computations are reused. One changed byte anywhere in the prefix invalidates everything after the change point.

**Pricing (per million tokens):**

| Model | Uncached Input | Cache Read (10x savings) |
|-------|---------------|-------------------------|
| Opus 4.6 | $5.00 | $0.50 |
| Sonnet 4.6 | $3.00 | $0.30 |
| Haiku 4.5 | $1.00 | $0.10 |

**Cache TTL:**
- Pro/API users: 5 minutes. Each cache hit resets the timer. Take 6 minutes between messages and the cache expires entirely.
- Max users: 1 hour (server-controlled).
- Minimum cacheable size: 1024-4096 tokens depending on model.

## What breaks the cache

Claude Code tracks 14 cache invalidation vectors internally:

1. Editing CLAUDE.md (especially top sections)
2. Dependency changes in the project
3. Configuration updates (settings.json, .mcp.json)
4. Memory mutations (if MEMORY.md is inlined in CLAUDE.md)
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

The top 4 are the ones most users trigger accidentally. cc-rig prevents all of them.

## What cc-rig does automatically

### Static-first CLAUDE.md

cc-rig orders CLAUDE.md so the content that never changes is at the top:

```
## Project Identity          <-- static, cached across all sessions
## Commands                  <-- static
## Guardrails                <-- static (includes 4 cache rules)
## Compaction Survival       <-- static
## Workflow Principles       <-- static
## Framework Rules           <-- static
## Agent Docs                <-- static (@import references)
## Memory                    <-- semi-static (pointers, not content)
...
## Current Context           <-- dynamic (last section, only this breaks cache)
```

Everything above "Current Context" is identical across sessions. Only the tail of the prefix changes, so the vast majority of tokens hit the cache.

### Cache guardrails

Every generated CLAUDE.md includes 4 unconditional rules that tell Claude how to preserve the cache:

```
- Never edit CLAUDE.md during a session. Use CLAUDE.local.md for notes.
- Never toggle hooks, MCP servers, or plugins mid-session.
- Never switch models mid-conversation. Use subagents for model escalation.
- Load memory via Read tool at runtime. Never paste memory into CLAUDE.md.
```

Claude sees these on startup and follows them. Without these rules, Claude will sometimes suggest editing CLAUDE.md or switching models, which silently invalidates the cache.

### Memory via Read tool

Team memory files (`memory/decisions.md`, `memory/patterns.md`, etc.) are loaded via the Read tool on demand, not inlined in CLAUDE.md. If memory were baked into CLAUDE.md, every session would have a different prefix (since memory changes every session) and the cache would never hit.

### Compaction survival

When Claude Code's context window fills up (~95%), it compacts the conversation into a summary. This can lose critical project context. cc-rig generates:

1. A "Compaction Survival" section in CLAUDE.md that tells Claude exactly what to preserve (project name, stack, commands, directories) and what to discard.
2. A PreCompact hook (B1+ harness) that fires before compaction and outputs the project essentials, ensuring they appear in the compaction summary.

### Session telemetry (B2+ harness)

The `session-telemetry.sh` Stop hook writes a JSONL record after every session:

```json
{
  "timestamp": "2026-04-03T14:30:00+0000",
  "turn_count": 42,
  "model": "sonnet",
  "input_tokens": 125000,
  "output_tokens": 48000,
  "estimated_cost_usd": 0.0712,
  "compaction_count": 1
}
```

This gives you visibility into where your tokens are going.

### Fork-session for parallel work

For workflows that support it (spec-driven, aihero, superpowers), cc-rig generates guidance about `--fork-session`. Forking shares the cached prefix across parallel investigations:

- 3 independent sessions: 3 x 1.25x = 3.75x cache write cost
- 3 forked sessions: 1 x 1.25x + 2 x 0.1x = 1.45x cache write cost

## Checking your cache health

### cc-rig doctor

`cc-rig doctor` runs two cache-specific checks:

**CLAUDE.md cache-friendliness**: Scans the static zone (everything above "## Current Context") for dates, timestamps and "Updated:" markers. These change every session and break the cache.

```
$ cc-rig doctor
...
⚠ CLAUDE.md line 8: date in static section. Move to Current Context
  or CLAUDE.local.md to avoid cache breaks.
⚠ Cache health: 28% hit ratio in most recent session (target: >40%).
  See agent_docs/cache-friendly-workflow.md.
```

**Cache health**: Parses your most recent Claude Code session JSONL (in `~/.claude/projects/`) and calculates the ratio of `cache_read_input_tokens` to total cache tokens. Warns if it drops below 40%.

### Manual check

You can inspect your own session files:

```bash
# Find your project's session directory
ls ~/.claude/projects/

# Check the most recent session's cache stats
cat ~/.claude/projects/-path-to-project/*.jsonl | \
  python3 -c "
import sys, json
cr, cc = 0, 0
for line in sys.stdin:
    d = json.loads(line)
    if d.get('type') == 'assistant':
        u = d.get('message', {}).get('usage', {})
        cr += u.get('cache_read_input_tokens', 0)
        cc += u.get('cache_creation_input_tokens', 0)
total = cr + cc
print(f'Cache read: {cr:,}  Cache creation: {cc:,}')
print(f'Hit ratio: {cr/total:.0%}' if total else 'No data')
"
```

A healthy session shows >80% cache read ratio after the first few turns.

## Rules of thumb

1. **Never edit CLAUDE.md during a session.** Use `CLAUDE.local.md` for session notes. Edit CLAUDE.md between sessions.
2. **Never switch models.** Use the Task tool (subagents) to escalate to Opus for specific tasks. The main conversation keeps its cache.
3. **Don't toggle anything mid-session.** Hooks, MCP servers, plugins, web search, speed settings. Set them before you start.
4. **Keep dynamic content at the bottom.** If you add a "Current Task" or "Session Notes" section, put it at the very end of CLAUDE.md.
5. **Load memory on demand.** Use the Read tool to load `memory/decisions.md` when you need it, not by pasting it into CLAUDE.md.
6. **Respond within 5 minutes** (Pro users). The cache TTL is 5 minutes. If you take longer than that between messages, the entire cache expires and must be rebuilt. Max users have 1 hour.
7. **Use `--fork-session` for parallel work.** Forked sessions share the cached prefix.
