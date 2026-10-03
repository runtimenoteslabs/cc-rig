# Demo 8: cc-rig tune -- score, fix, re-score
# Shows: a hand-grown CLAUDE.md scored against a month of session logs,
# then `--fix` applying the safe fixes with a diff and the new score.
# The logs are synthetic (assets/demo-data/generate_tune_sessions.py):
# 44 Opus 5.5 sessions with 1-hour cache writes, like real Claude Code.
# Duration: ~40s

Output assets/demo-8-tune.gif
Output assets/demo-8-tune.mp4

Set Shell "bash"
Set FontSize 20
Set Width 1920
Set Height 1080
Set Padding 24
Set TypingSpeed 50ms
Set Framerate 12

# ── Hidden setup ──────────────────────────────────────────────────────────
# HOME=/tmp/demo-tune/home, project at /tmp/demo-tune/acme-api
# (session logs go in the matching -tmp-demo-tune-acme-api projects dir).
Hide
Type "export PATH=/home/exitcode42/python_projects/claude-boot/.venv/bin:$PATH"
Enter
Sleep 200ms
Type "export HOME=/tmp/demo-tune/home"
Enter
Sleep 200ms
Type "export PS1='$ '"
Enter
Sleep 200ms
Type "rm -rf /tmp/demo-tune && mkdir -p /tmp/demo-tune/acme-api/.claude && cd /tmp/demo-tune/acme-api"
Enter
Sleep 200ms
Type "python3 /home/exitcode42/python_projects/claude-boot/assets/demo-data/generate_tune_sessions.py /tmp/demo-tune/home/.claude/projects/-tmp-demo-tune-acme-api"
Enter
Sleep 500ms
Type "cp /home/exitcode42/python_projects/claude-boot/assets/demo-data/acme-api-CLAUDE.md CLAUDE.md && echo '{}' > .claude/settings.json"
Enter
Sleep 200ms
Type "clear"
Enter
Sleep 300ms
Show

# ── A CLAUDE.md that grew by hand ─────────────────────────────────────────
Type "# A CLAUDE.md that grew by hand. How healthy is it?"
Enter
Sleep 1200ms
Type "cat CLAUDE.md"
Enter
Sleep 4000ms

# ── Score it ──────────────────────────────────────────────────────────────
Type "clear"
Enter
Sleep 300ms
Type "cc-rig tune"
Enter
Sleep 9000ms

# ── Fix the safe ones ─────────────────────────────────────────────────────
Type "clear"
Enter
Sleep 300ms
Type "cc-rig tune --fix"
Enter
Sleep 9000ms

# ── CTA ───────────────────────────────────────────────────────────────────
Type "clear"
Enter
Sleep 300ms
Type "# cc-rig tune --ci gates a pipeline on the score."
Enter
Type "# github.com/runtimenoteslabs/cc-rig"
Enter
Sleep 4000ms
