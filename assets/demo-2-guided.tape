# Demo 2: Guided + Expert Mode (v2 — Workflow-first)
# Shows: cc-rig init → Welcome → Gstack workflow → Django stack → Basics → Expert tabs → Features (locked) → Lite harness → tree + cat
# Flow: Welcome → Workflow → Template → Basics → Review → Expert → Features → SkillPacks → Harness → Confirm
# Duration: ~90s

Output assets/demo-2-guided.gif

Set Shell "bash"
Set FontSize 18
Set Width 1920
Set Height 1080
Set Padding 16
Set TypingSpeed 40ms

# Setup (hidden)
Hide
Type "export PATH=/home/exitcode42/python_projects/claude-boot/.venv/bin:$PATH CC_RIG_OFFLINE=1"
Enter
Sleep 500ms
Type "rm -rf /tmp/demo-guided && mkdir -p /tmp/demo-guided && cd /tmp/demo-guided"
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 300ms
Show

# ── Title card ──
Type "# cc-rig: Guided setup with expert customization"
Enter
Sleep 2000ms
Type ""
Enter
Type "cc-rig init"
Enter
Sleep 3500ms

# ─── Screen 1: WelcomeScreen ───
# RadioSet focused on "Fresh project". Tab → Start button, Space to press.
Sleep 3000ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 2: WorkflowScreen (workflow first!) ───
# speedrun(0) → standard(1) → gstack(2)
Sleep 1500ms
Down
Sleep 1200ms
Down
Sleep 1500ms
# Pause on gstack detail panel
Sleep 3500ms
# Tab: RadioSet → Back → Next. Tab Tab Space = Next.
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 3: TemplateScreen (stack is secondary) ───
# generic(0) is default. Down to fastapi(1), down to django(2).
Sleep 1500ms
Down
Sleep 800ms
Down
Sleep 1500ms
# Pause on Django
Sleep 2000ms
# Tab: RadioSet → Back → Next
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 4: BasicsScreen ───
# Name input focused. Type name, tab to desc, type desc, tab to Next area.
Sleep 800ms
Type "my-django-app"
Sleep 500ms
Tab
Sleep 300ms
Type "A Django app with gstack workflow"
Sleep 500ms
# Tab: desc → output-dir → in-place checkbox → Back → Next
Tab
Sleep 200ms
Tab
Sleep 200ms
Tab
Sleep 200ms
Space
Sleep 2500ms

# ─── Screen 5: ReviewScreen ───
# Summary shown. Checkbox "Customize?" is focused. Space to toggle ON.
Sleep 2500ms
Space
Sleep 2000ms
# Tab: checkbox → Back → Next
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 6: ExpertScreen ───
# Agents tab visible. Browse all 4 tabs with number keys.
Sleep 3000ms
Type "2"
Sleep 3000ms
Type "3"
Sleep 3000ms
Type "4"
Sleep 3000ms
Type "1"
Sleep 2000ms
# Tab: SelectionList → Back → Next
Tab
Sleep 500ms
Tab
Sleep 500ms
Space
Sleep 2500ms

# ─── Screen 7: FeaturesScreen (with workflow locking!) ───
# gstack: memory [included], spec [not available], gtd [not available], worktrees [included]
# Disabled checkboxes can't be focused via Tab, so Tab skips them.
# Show the screen for a moment, then proceed.
Sleep 3000ms
Sleep 2000ms
# Find Next button. Disabled checkboxes are skipped by Tab.
# Tab from first focusable → eventually reaches Back → Next
Tab
Sleep 500ms
Tab
Sleep 500ms
Space
Sleep 2500ms

# ─── Screen 8: SkillPacksScreen ───
# Select Security pack (first checkbox, focused)
Sleep 1500ms
Space
Sleep 1000ms
# Tab through remaining packs → Back → Next
Tab
Sleep 150ms
Tab
Sleep 150ms
Tab
Sleep 150ms
Tab
Sleep 150ms
Tab
Sleep 150ms
Tab
Sleep 200ms
Space
Sleep 2500ms

# ─── Screen 9: HarnessScreen ───
# Select Lite (B1) — down once from None
Sleep 1500ms
Down
Sleep 2500ms
Sleep 2000ms
# Tab: RadioSet → Back → Next
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 10: ConfirmScreen ───
# Generate button auto-focused. Space to confirm.
Sleep 3000ms
Space
Sleep 5000ms

# ── Output exploration — narrated sections ──

# Section 1: .claude/ directory structure
Type "clear"
Enter
Sleep 500ms
Type "# What cc-rig generated — your .claude/ directory"
Enter
Sleep 1500ms
Type "tree --dirsfirst -L 2 .claude/"
Enter
Sleep 6000ms

# Section 2: CLAUDE.md top — project identity, stack, commands
Type "clear"
Enter
Sleep 500ms
Type "# The generated CLAUDE.md — project identity and commands"
Enter
Sleep 1500ms
Type "head -40 CLAUDE.md"
Enter
Sleep 6000ms

# Section 3: CLAUDE.md — process skills section
Type "clear"
Enter
Sleep 500ms
Type "# Process skills — installed from garrytan/gstack"
Enter
Sleep 1500ms
Type "sed -n '41,80p' CLAUDE.md"
Enter
Sleep 6000ms

# ── CTA ──
Type "clear"
Enter
Sleep 500ms
Type ""
Enter
Type "# Get started:"
Enter
Type "#   pip install cc-rig"
Enter
Type "#   github.com/runtimenoteslabs/cc-rig"
Enter
Type ""
Enter
Type "# One command. Complete Claude Code setup."
Enter
Sleep 5000ms
