# Demo 4: Full Showcase — Everything in cc-rig (v2 — Workflow-first)
# Shows: Browse all 7 workflows, all 16 templates, expert mode, features (locked), harness, skill packs
# Flow: Welcome → Workflow → Template → Basics → Review → Expert → Features → SkillPacks → Harness → Confirm
# Duration: ~120s

Output assets/demo-4-showcase.gif

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
Type "rm -rf /tmp/demo-showcase && mkdir -p /tmp/demo-showcase && cd /tmp/demo-showcase"
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 300ms
Show

# ── Title card ──
Type "# cc-rig: Complete showcase — 7 workflows x 16 templates x 6 harness levels"
Enter
Sleep 2500ms
Type ""
Enter
Type "cc-rig init"
Enter
Sleep 3500ms

# ─── Screen 1: WelcomeScreen ───
# Browse the launch modes
Sleep 2000ms
Down
Sleep 1500ms
Down
Sleep 1500ms
Down
Sleep 1500ms
Down
Sleep 1500ms
# Back to "Fresh project"
Up
Sleep 500ms
Up
Sleep 500ms
Up
Sleep 500ms
Up
Sleep 500ms
Sleep 1500ms
# Tab → Start button, Space
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 2: WorkflowScreen (FIRST — workflow-first in v2!) ───
# Browse ALL 7 workflows with detail panels
# speedrun(0) → standard(1) → gstack(2) → aihero(3) → spec-driven(4) → superpowers(5) → gtd(6)
Sleep 1500ms
Down
Sleep 2500ms
Down
Sleep 2500ms
Down
Sleep 2500ms
Down
Sleep 2500ms
# superpowers
Down
Sleep 3000ms
# Pause on superpowers — this is our pick
Sleep 2000ms
# gtd (show it exists)
Down
Sleep 2500ms
# Back to superpowers
Up
Sleep 1500ms
# Tab: RadioSet → Back → Next
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 3: TemplateScreen (stack is secondary) ───
# Browse ALL 16 templates
# generic(0) through phoenix(15)
Sleep 1500ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 800ms
Down
Sleep 1500ms
# Now on Phoenix (index 15)
Sleep 2500ms
# Tab: RadioSet → Back → Next
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 4: BasicsScreen ───
Sleep 800ms
Type "phoenix-showcase"
Sleep 500ms
Tab
Sleep 300ms
Type "Full cc-rig showcase with superpowers workflow"
Sleep 500ms
# Tab: desc → output-dir → in-place → Back → Next
Tab
Sleep 200ms
Tab
Sleep 200ms
Tab
Sleep 200ms
Space
Sleep 2500ms

# ─── Screen 5: ReviewScreen ───
# Check customize for expert mode
Sleep 3000ms
Space
Sleep 2000ms
Tab
Sleep 200ms
Tab
Sleep 200ms
Space
Sleep 2500ms

# ─── Screen 6: ExpertScreen ───
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
# superpowers: memory [included], spec [included], gtd [not available], worktrees [included]
# Most checkboxes disabled. Show for a moment then proceed.
Sleep 3000ms
Sleep 2000ms
# Tab skips disabled checkboxes → reaches Back → Next
Tab
Sleep 500ms
Tab
Sleep 500ms
Space
Sleep 2500ms

# ─── Screen 8: SkillPacksScreen (workflow-aware labels!) ───
# Superpowers is comprehensive — packs show overlap/depth labels
Sleep 1500ms
# Toggle Security
Space
Sleep 1000ms
Tab
Sleep 300ms
Tab
Sleep 300ms
Tab
Sleep 300ms
# Toggle Code Quality
Space
Sleep 1000ms
# Skip Database Pro → Back → Next
Tab
Sleep 150ms
Tab
Sleep 150ms
Tab
Sleep 200ms
Space
Sleep 2500ms

# ─── Screen 9: HarnessScreen ───
# Browse to Standard (B2)
Sleep 1500ms
Down
Sleep 2000ms
Down
Sleep 2500ms
# Pause on Standard B2
Sleep 2000ms
# Tab: RadioSet → Back → Next
Tab
Sleep 300ms
Tab
Sleep 300ms
Space
Sleep 2500ms

# ─── Screen 10: ConfirmScreen ───
Sleep 3000ms
Space
Sleep 5000ms

# ── Output exploration ──

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

# Section 2: CLAUDE.md top
Type "clear"
Enter
Sleep 500ms
Type "# The generated CLAUDE.md — project identity and commands"
Enter
Sleep 1500ms
Type "head -40 CLAUDE.md"
Enter
Sleep 6000ms

# Section 3: CLAUDE.md — process skills + workflow principles
Type "clear"
Enter
Sleep 500ms
Type "# Process skills from obra/superpowers + workflow principles"
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
