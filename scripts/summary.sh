#!/usr/bin/env bash
# summary.sh — Quick project status and capability overview
# Usage: bash summary.sh [project_dir]
set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║      Tech Essay Writer — Project Summary         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Pipeline status
if [ -f "$PROJECT_DIR/.essay-state/pipeline-state.json" ]; then
  echo "📄 Active Pipeline:"
  python3 -c "
import json
with open('$PROJECT_DIR/.essay-state/pipeline-state.json') as f:
    d = json.load(f)
print(f'   Topic:    {d.get(\"topic\", \"(none)\")}')
print(f'   Stage:    {d.get(\"stage\", \"unknown\")}')
print(f'   Language: {d.get(\"language\", \"en\")}')
print(f'   Draft v:  {d.get(\"draft_version\", 0)}')
print(f'   Reviews:  {len(d.get(\"reviews\", {}))}/8')
print(f'   Complete: {d.get(\"completed\", False)}')
" 2>/dev/null || echo "   (could not read pipeline state)"
  echo ""

  # Quality score
  if [ -f "$PROJECT_DIR/.essay-state/quality-score.json" ]; then
    python3 -c "
import json
with open('$PROJECT_DIR/.essay-state/quality-score.json') as f:
    d = json.load(f)
print(f'   Quality: {d.get(\"composite_score\", \"?\")}/10 ({d.get(\"readiness\", \"?\")})')
" 2>/dev/null
  fi

  # Checkpoints
  if [ -d "$PROJECT_DIR/.essay-state/checkpoints" ] && [ -f "$PROJECT_DIR/.essay-state/checkpoints/index.json" ]; then
    CP_COUNT=$(python3 -c "import json; print(len(json.load(open('$PROJECT_DIR/.essay-state/checkpoints/index.json'))))" 2>/dev/null || echo "0")
    echo "   Checkpoints: $CP_COUNT saved"
  fi
else
  echo "📄 No active pipeline. Start one with /tech-essay-writer."
fi

echo ""

# Capabilities
echo "🔧 Capabilities:"
echo "   Pipeline:    7-stage (intake → research → outline → draft → review → refine → polish)"
echo "   Reviewers:   8 agents (technical, editor, adversarial, audience, seo, external, factcheck, chinese)"
echo "   Platforms:   7 (internal, external, medium, dev.to, hashnode, wechat, juejin)"
echo "   Templates:   $(ls "$SKILL_DIR/templates/"*.md 2>/dev/null | wc -l | tr -d ' ') article types"
echo "   Languages:   English + Chinese (with platform-specific formatting)"
echo ""

# Author profile
echo "👤 Author Profile:"
if [ -f "$HOME/.tech-essay-writer/author-profile.json" ]; then
  python3 -c "
import json
with open('$HOME/.tech-essay-writer/author-profile.json') as f:
    d = json.load(f)
name = d.get('name', '(not set)')
bio = d.get('bio', '(not set)')
expertise = ', '.join(d.get('expertise', [])) or '(not set)'
print(f'   Name:      {name}')
print(f'   Bio:       {bio[:60]}...' if len(bio) > 60 else f'   Bio:       {bio}')
print(f'   Expertise: {expertise}')
" 2>/dev/null
else
  echo "   Not configured. Run: bash scripts/author-profile.sh init"
fi
echo ""

# Taste memory
echo "🎨 Taste Memory:"
if [ -f "$HOME/.tech-essay-writer/taste-memory.json" ]; then
  python3 -c "
import json
with open('$HOME/.tech-essay-writer/taste-memory.json') as f:
    d = json.load(f)
articles = d.get('articles_written', 0)
patterns = len(d.get('learned_patterns', []))
prefs = len(d.get('explicit_preferences', []))
print(f'   Articles tracked: {articles}')
print(f'   Learned patterns: {patterns}')
print(f'   Explicit prefs:   {prefs}')
" 2>/dev/null
else
  echo "   No taste data yet. It builds as you write articles."
fi
echo ""

# Expertise graph
echo "📊 Expertise Graph:"
if [ -f "$HOME/.tech-essay-writer/expertise-graph.json" ]; then
  python3 -c "
import json
with open('$HOME/.tech-essay-writer/expertise-graph.json') as f:
    d = json.load(f)
topics = d.get('topics', {})
if topics:
    sorted_t = sorted(topics.items(), key=lambda x: x[1].get('authority_score', 0), reverse=True)
    for name, data in sorted_t[:5]:
        score = data.get('authority_score', 0)
        count = data.get('article_count', 0)
        print(f'   {name}: {score:.1f} authority ({count} articles)')
else:
    print('   No topics tracked yet.')
" 2>/dev/null
else
  echo "   No expertise data yet."
fi
echo ""

# Published articles
echo "📚 Published Articles:"
if [ -f "$HOME/.tech-essay-writer/published-articles.json" ]; then
  python3 -c "
import json
with open('$HOME/.tech-essay-writer/published-articles.json') as f:
    d = json.load(f)
articles = d.get('articles', [])
print(f'   Total: {len(articles)}')
for a in articles[-3:]:
    print(f'   • {a.get(\"title\", \"?\")[:50]}')
" 2>/dev/null
else
  echo "   None yet. Publish your first article!"
fi
echo ""

# Config
echo "⚙️  Configuration:"
if [ -f "$HOME/.tech-essay-writer/config.json" ]; then
  python3 -c "
import json
with open('$HOME/.tech-essay-writer/config.json') as f:
    d = json.load(f)
lang = d.get('language', 'en')
platforms = ', '.join(d.get('default_platforms', [])) or '(none)'
print(f'   Language:  {lang}')
print(f'   Platforms: {platforms}')
" 2>/dev/null
else
  echo "   Using defaults. Run: bash scripts/config.sh init"
fi
echo ""
echo "Run 'bash scripts/dry-run.sh <dir>' to test the pipeline."
