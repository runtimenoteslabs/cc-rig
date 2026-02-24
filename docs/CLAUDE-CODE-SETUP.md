# Getting Started with Claude Code + cc-rig

This guide walks you through setting up Claude Code with cc-rig for a new or existing project.

## Prerequisites

1. **Claude Code** installed and working (`claude --version`)
2. **Python 3.9+** for running cc-rig
3. **A project** (or an idea for one)

## Step 1: Install cc-rig

```bash
pip install cc-rig
```

Verify:

```bash
cc-rig --version
```

## Step 2: Generate Configuration

### New project

```bash
mkdir my-project && cd my-project
cc-rig init --template fastapi --workflow standard --name my-project
```

### Existing project

```bash
cd my-existing-project
cc-rig init --migrate
```

cc-rig detects your stack from project files (`pyproject.toml`, `package.json`, `go.mod`, etc.) and generates matching configuration.

### Not sure what to pick?

```bash
cc-rig init --quick
```

or browse available options:

```bash
cc-rig preset list
```

## Step 3: Review Generated Files

After generation, you'll have:

```
my-project/
  CLAUDE.md                        # Main Claude context file
  .claude/
    settings.json                  # Permissions and hooks
    agents/                        # Agent definitions
    commands/                      # Slash commands
    skills/                        # Bundled skills
    hooks/                         # Hook shell scripts
  agent_docs/                      # Project documentation for Claude
  memory/                          # Persistent memory (if enabled)
  .cc-rig.json                     # Saved config
  .claude/.cc-rig-manifest.json    # File tracking manifest
```

## Step 4: Start Claude Code

```bash
claude
```

Claude Code will automatically read `CLAUDE.md` and `.claude/settings.json` on startup. Your agents, commands, and hooks are immediately available.

## Step 5: Verify Setup

```bash
cc-rig doctor
```

This checks that all generated files are present, valid, and consistent.

## Optional: Add Runtime Harness

For task tracking and verification discipline:

```bash
cc-rig harness init              # Standard: verification gates
cc-rig harness init --lite       # Lite: just task tracking
cc-rig harness init --autonomy   # Full autonomous operation
```

## Optional: Save Config for Team

```bash
# Save for yourself
cc-rig config save my-setup

# Export for team (strips machine-specific paths)
cc-rig config save --export team-config.json --portable

# Lock to prevent modification
cc-rig config lock my-setup
```

Teammates can then:

```bash
cc-rig init --config team-config.json
```

## Cleanup

To remove all cc-rig generated files:

```bash
cc-rig clean
```

This only removes files tracked in the manifest. Your code and non-cc-rig files are untouched.

## Troubleshooting

### Claude doesn't see my config

- Check that `CLAUDE.md` exists in the project root
- Check that `.claude/settings.json` is valid JSON: `cc-rig doctor`
- Restart Claude Code after generating config

### Hooks aren't firing

- Check hook scripts are executable: `cc-rig doctor --fix`
- Check `.claude/settings.json` has the hooks section
- Verify the hook event type matches your action

### Memory files are empty

- Memory files start empty — they're populated during Claude Code sessions
- The Stop hook prompts Claude to save learnings
- Use `/remember` command to manually save insights
