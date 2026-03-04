# Official Claude Code Plugin Integration

As of v1.4.0, cc-rig curates official Anthropic marketplace plugins alongside skills, hooks, agents, commands, and MCPs. Smart defaults resolve plugins automatically based on your language, template, and workflow.

---

## Plugin Catalog (24 plugins, 5 categories)

### LSP (7 plugins)

Language Server Protocol plugins provide diagnostics, go-to-definition, and refactoring support. Each requires the corresponding binary on PATH.

| Plugin | Description | Requires Binary |
|--------|-------------|-----------------|
| `pyright-lsp` | Python type checking and diagnostics via Pyright | `pyright` |
| `typescript-lsp` | TypeScript diagnostics and go-to-definition | `typescript-language-server` |
| `gopls-lsp` | Go language server with diagnostics and refactoring | `gopls` |
| `rust-analyzer-lsp` | Rust diagnostics, completion, and code actions | `rust-analyzer` |
| `jdtls-lsp` | Java language server with Eclipse JDT | `jdtls` |
| `csharp-lsp` | C# diagnostics via OmniSharp | `OmniSharp` |
| `php-lsp` | PHP language server with Intelephense | `intelephense` |

### Integration (10 plugins)

Service integrations that connect Claude Code to external platforms. All are self-contained (no external binary required).

| Plugin | Description |
|--------|-------------|
| `github` | GitHub integration (PRs, issues, actions) |
| `vercel` | Vercel deployment and project management |
| `supabase` | Supabase database and auth management |
| `sentry` | Sentry error tracking and performance monitoring |
| `slack` | Slack messaging and workspace integration |
| `linear` | Linear issue tracking and project management |
| `notion` | Notion workspace and documentation integration |
| `firebase` | Firebase backend services and hosting |
| `gitlab` | GitLab repository and CI/CD integration |
| `atlassian` | Jira and Confluence integration |

### Workflow (5 plugins)

Development workflow automation plugins.

| Plugin | Description |
|--------|-------------|
| `commit-commands` | Smart commit message generation and staging |
| `code-review` | Automated code review with inline comments |
| `pr-review-toolkit` | Pull request review with approval workflows |
| `feature-dev` | Feature development lifecycle management |
| `security-guidance` | Security best practices and vulnerability detection |

### Autonomy (1 plugin)

| Plugin | Description |
|--------|-------------|
| `ralph-loop` | Official Anthropic autonomous iteration loop |

### Utility (1 plugin)

| Plugin | Description |
|--------|-------------|
| `hookify` | Visual hook builder and manager |

---

## Smart Defaults: How Plugins Are Resolved

cc-rig resolves plugins automatically from three axes:

### 1. Language -> LSP Plugin

Your project language determines which LSP plugin is included.

| Language | LSP Plugin |
|----------|------------|
| Python | `pyright-lsp` |
| TypeScript | `typescript-lsp` |
| Go | `gopls-lsp` |
| Rust | `rust-analyzer-lsp` |
| Java | `jdtls-lsp` |
| C# | `csharp-lsp` |
| PHP | `php-lsp` |
| Ruby, Elixir, Generic | No official LSP plugin yet |

### 2. Template -> Integration Plugins

Your template determines which integration plugins are included.

| Template | Integration Plugins |
|----------|-------------------|
| All templates | `github` |
| `nextjs` | `github`, `vercel` |

The `github` plugin is included for every template. Next.js additionally gets `vercel` for deployment management.

### 3. Workflow -> Workflow Plugins

Your workflow determines which workflow plugins are included. These are cumulative.

| Workflow | Workflow Plugins |
|----------|-----------------|
| speedrun | `commit-commands` |
| standard | `commit-commands`, `code-review` |
| spec-driven | `commit-commands`, `code-review`, `feature-dev`, `pr-review-toolkit` |
| gtd-lite | `commit-commands`, `code-review` |
| verify-heavy | `commit-commands`, `code-review`, `pr-review-toolkit`, `security-guidance` |

---

## settings.json: `enabledPlugins` Format

cc-rig writes resolved plugins to `.claude/settings.json` in the `enabledPlugins` section. The format is `"name@marketplace": true`:

```json
{
  "enabledPlugins": {
    "pyright-lsp@claude-plugins-official": true,
    "github@claude-plugins-official": true,
    "commit-commands@claude-plugins-official": true,
    "code-review@claude-plugins-official": true
  }
}
```

All plugins in the catalog use the `claude-plugins-official` marketplace.

---

## GitHub Plugin Replaces GitHub MCP

The `github` integration plugin replaces the previous GitHub MCP server configuration. The plugin is self-contained and auto-starts -- no `.mcp.json` entry needed, no `npx` dependency, no manual server configuration.

When the `github` plugin is resolved, cc-rig automatically removes `github` from the MCP list to avoid duplication. Other MCPs (postgres, playwright, etc.) continue to be configured in `.mcp.json` as before.

---

## Ralph-Loop Plugin

The `ralph-loop` plugin is the official Anthropic autonomous iteration loop. It provides an alternative to cc-rig's built-in `loop.sh` harness script.

**Key differences from loop.sh:**

- Marketplace plugin (Anthropic-maintained, always up to date)
- Integrated directly into Claude Code's runtime
- Not resolved by smart defaults -- explicitly selected via harness picker

**Harness picker integration:**

The harness configuration screen shows a 6th option for ralph-loop. When selected, it offers custom-style feature confirms for `task_tracking` and `budget_awareness` (B1/B2 features). Ralph-loop and `autonomy_loop` (loop.sh) are mutually exclusive -- selecting one disables the other.

**Schema validation** enforces this mutual exclusion: a config cannot have both `ralph_loop: true` and `autonomy_loop: true`.

---

## Expert Mode: Plugin Customization

In expert mode, the plugins category provides a multi-select from the full 24-plugin catalog. This is available in both the TUI wizard (dedicated Plugins tab in ExpertScreen) and the CLI flow.

The computed defaults are pre-filled based on your language, template, and workflow. You can add or remove individual plugins as needed.

---

## Doctor Check: LSP Binary Detection

`cc-rig doctor` includes a plugin health check that verifies LSP binaries are available on PATH. If a resolved LSP plugin requires a binary that is not found (e.g., `pyright` for `pyright-lsp`), doctor reports a **warning** (not an error -- the plugin will still be configured, but diagnostics will not work until the binary is installed).

Example output:

```
[WARN] Plugin pyright-lsp requires binary 'pyright' but it was not found on PATH
       Install: pip install pyright
```

---

## MCP Servers (Still Supported)

MCPs continue to work alongside plugins for services without a plugin equivalent:

| Server | Purpose |
|--------|---------|
| postgres | PostgreSQL read-only queries |
| sqlite | SQLite database access |
| playwright | Browser automation and testing |
| filesystem | File system access (built-in) |

See [mcp-setup.md](mcp-setup.md) for MCP configuration details.

## IDE Extensions

cc-rig generates files that work with Claude Code in any environment:

- **VS Code** -- Claude Code extension (official)
- **JetBrains** -- Claude Code plugin
- **Terminal** -- `claude` CLI directly
