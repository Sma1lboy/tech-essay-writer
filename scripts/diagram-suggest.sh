#!/usr/bin/env bash
# Diagram and image suggestion engine — analyzes markdown content and suggests
# where architecture diagrams, flow charts, comparison tables, sequence diagrams,
# or screenshots would improve comprehension. Outputs Mermaid syntax where possible.
# Usage: diagram-suggest.sh <markdown_file> [--verbose]
set -euo pipefail

MARKDOWN_FILE="${1:-}"
VERBOSE="${2:-}"

if [ -z "$MARKDOWN_FILE" ]; then
  cat <<'EOF'
Usage: diagram-suggest.sh <markdown_file> [--verbose]

Analyzes markdown and suggests where visual aids would improve comprehension.
Outputs Mermaid syntax for each suggestion where possible.

Types: flowchart, sequence, class, state, er, comparison_table, architecture, timeline
EOF
  exit 1
fi

if [ ! -f "$MARKDOWN_FILE" ]; then
  echo '{"error":"file not found","file":"'"$MARKDOWN_FILE"'"}'
  exit 1
fi

# Determine state dir — look for .essay-state/ relative to the markdown file
STATE_DIR=""
parent="$(dirname "$MARKDOWN_FILE")"
if [ "$(basename "$parent")" = ".essay-state" ]; then
  STATE_DIR="$parent"
elif [ -d "$parent/.essay-state" ]; then
  STATE_DIR="$parent/.essay-state"
fi

python3 - "$MARKDOWN_FILE" "$VERBOSE" "$STATE_DIR" << 'PYEOF'
import json, re, sys, os

md_file = sys.argv[1]
verbose = len(sys.argv) > 2 and sys.argv[2] == "--verbose"
state_dir = sys.argv[3] if len(sys.argv) > 3 else ""

with open(md_file, "r", encoding="utf-8") as f:
    content = f.read()

# --- Language detection ---
chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
total_chars = max(len(content), 1)
is_chinese = (chinese_chars / total_chars) > 0.1

def label(en, zh):
    return zh if is_chinese else en

# --- Section parsing ---
lines_all = content.split('\n')
sections = []
current_section = {"heading": "(intro)", "level": 0, "start_line": 1, "lines": []}

for i, line in enumerate(lines_all):
    heading_match = re.match(r'^(#{1,6})\s+(.+)', line)
    if heading_match:
        if current_section["lines"] or current_section["heading"] == "(intro)":
            current_section["content"] = '\n'.join(current_section["lines"])
            sections.append(current_section)
        current_section = {
            "heading": heading_match.group(2).strip(),
            "level": len(heading_match.group(1)),
            "start_line": i + 1,
            "lines": []
        }
    else:
        current_section["lines"].append(line)

current_section["content"] = '\n'.join(current_section["lines"])
sections.append(current_section)

# --- Strip code blocks from prose for analysis ---
def strip_code_blocks(text):
    return re.sub(r'```[\s\S]*?```', '', text)

# --- Detection functions ---

def detect_architecture(text):
    signals = []
    arch_kw = re.findall(
        r'\b(component|service|layer|module|microservice|backend|frontend|'
        r'middleware|gateway|proxy|load.balancer|database|cache|queue|broker|'
        r'monolith|client.server)\b',
        text, re.IGNORECASE)
    if len(arch_kw) >= 2:
        signals.append(f"architecture keywords ({', '.join(set(k.lower() for k in arch_kw[:4]))})")
    conn_kw = re.findall(
        r'\b(connects? to|communicates? with|depends? on|integrates? with|'
        r'talks? to|interfaces? with|interacts? with)\b',
        text, re.IGNORECASE)
    if conn_kw:
        signals.append(f"connection language ({', '.join(conn_kw[:2])})")
    if re.search(r'\b(architecture|system design|infrastructure|topology|stack)\b', text, re.IGNORECASE):
        signals.append("system design language")
    # Chinese
    if re.search(r'(架构|系统设计|组件|服务层|微服务|中间件|网关)', text):
        signals.append(label("Chinese architecture terms", "架构相关术语"))
    return signals

def detect_flowchart(text):
    signals = []
    if re.search(r'\bfirst\b.*\bthen\b', text, re.IGNORECASE | re.DOTALL):
        signals.append("sequential flow (first...then)")
    if re.search(r'\bstep\s+\d', text, re.IGNORECASE):
        signals.append("numbered steps")
    seq_verbs = re.findall(
        r'\b(begins?|starts?|next|then|after that|finally|afterwards|'
        r'subsequently|followed by|leads? to|proceeds?)\b',
        text, re.IGNORECASE)
    if len(seq_verbs) >= 2:
        signals.append(f"sequential verbs ({', '.join(seq_verbs[:3])})")
    if re.search(r'\b(pipeline|workflow|process|procedure|flow)\b', text, re.IGNORECASE):
        if re.search(r'\b(step|stage|phase)\b', text, re.IGNORECASE):
            signals.append("workflow/pipeline with stages")
    ordered_items = re.findall(r'^\d+\.\s+', text, re.MULTILINE)
    if len(ordered_items) >= 3:
        signals.append(f"ordered list ({len(ordered_items)} items)")
    # Chinese
    if re.search(r'(步骤|流程|阶段|第[一二三四五六七八九十]步)', text):
        signals.append(label("Chinese process terms", "流程相关术语"))
    return signals

def detect_comparison(text):
    signals = []
    if re.search(r'\bvs\.?\b', text, re.IGNORECASE):
        signals.append("vs comparison")
    if re.search(r'\bcompared? to\b', text, re.IGNORECASE):
        signals.append("compared to")
    if re.search(r'\bpros?\s+(?:and|&)\s+cons?\b', text, re.IGNORECASE):
        signals.append("pros and cons")
    if re.search(r'\b(advantage|disadvantage|trade-?off|benefit|drawback)\b', text, re.IGNORECASE):
        if re.search(r'\b(but|however|while|whereas)\b', text, re.IGNORECASE):
            signals.append("trade-off discussion")
    if re.search(r'\bdifference[s]?\s+between\b', text, re.IGNORECASE):
        signals.append("differences between")
    if re.search(r'\b(option [A-C]|choice \d|approach \d)\b', text, re.IGNORECASE):
        signals.append("named options/choices")
    if re.search(r'\bon the other hand\b', text, re.IGNORECASE):
        signals.append("on the other hand")
    # Chinese
    if re.search(r'(对比|比较|优缺点|区别|优势|劣势)', text):
        signals.append(label("Chinese comparison terms", "对比相关术语"))
    return signals

def detect_state(text):
    signals = []
    if re.search(r'\bstate\b', text, re.IGNORECASE):
        if re.search(r'\b(transition|change|move|switch|enter|exit|from|to)\b', text, re.IGNORECASE):
            signals.append("state transitions")
    if re.search(r'\blifecycle\b', text, re.IGNORECASE):
        signals.append("lifecycle description")
    if re.search(r'\b(changes? from .+ to|transitions? from .+ to)\b', text, re.IGNORECASE):
        signals.append("explicit state change")
    state_words = re.findall(
        r'\b(pending|active|inactive|completed|failed|cancelled|archived|'
        r'draft|published|approved|rejected|idle|running|stopped|paused|'
        r'error|ready|waiting|processing|done|created|deleted|open|closed)\b',
        text, re.IGNORECASE)
    unique_states = set(s.lower() for s in state_words)
    if len(unique_states) >= 2:
        signals.append(f"multiple states ({', '.join(sorted(unique_states)[:4])})")
    if re.search(r'\bfsm\b|\bfinite state\b|\bstate machine\b', text, re.IGNORECASE):
        signals.append("state machine reference")
    # Chinese
    if re.search(r'(状态机|状态转换|生命周期|状态变更)', text):
        signals.append(label("Chinese state terms", "状态相关术语"))
    return signals

def detect_sequence(text):
    signals = []
    rr_kw = re.findall(
        r'\b(sends?|receives?|request|response|calls?|returns?|reply|'
        r'replies|responds?|acknowledges?)\b',
        text, re.IGNORECASE)
    if len(rr_kw) >= 2:
        signals.append(f"request/response language ({', '.join(set(k.lower() for k in rr_kw[:3]))})")
    if re.search(r'\b(client|server|user|api|endpoint|browser)\b', text, re.IGNORECASE):
        if re.search(r'\b(sends?|calls?|requests?|posts?|gets?)\b', text, re.IGNORECASE):
            signals.append("actor interaction")
    if re.search(r'\b(handshake|authentication flow|oauth|login flow|api call|http|grpc|websocket)\b', text, re.IGNORECASE):
        signals.append("protocol/API flow")
    msg_words = re.findall(
        r'\b(message|event|notification|callback|webhook|emit|publish|subscribe)\b',
        text, re.IGNORECASE)
    if len(msg_words) >= 2:
        signals.append(f"message passing ({', '.join(set(m.lower() for m in msg_words[:3]))})")
    # Chinese
    if re.search(r'(请求.*响应|调用|接口|消息传递)', text):
        signals.append(label("Chinese sequence terms", "时序相关术语"))
    return signals

def detect_er(text):
    signals = []
    if re.search(r'\b(has.many|belongs.to|one.to.many|many.to.many|one.to.one)\b', text, re.IGNORECASE):
        signals.append("relationship cardinality")
    if re.search(r'\b(entity|relationship|foreign.key)\b', text, re.IGNORECASE):
        signals.append("entity-relationship language")
    if re.search(r'\b(schema|data.model|database.model|table[s]?\s+(?:for|store|contain))\b', text, re.IGNORECASE):
        signals.append("data model description")
    if re.search(r'\b(primary.key|index|column|field|record)\b', text, re.IGNORECASE):
        if re.search(r'\b(table|relation|entity)\b', text, re.IGNORECASE):
            signals.append("database schema language")
    # Chinese
    if re.search(r'(实体|关系|外键|数据模型|主键)', text):
        signals.append(label("Chinese ER terms", "数据模型相关术语"))
    return signals

def detect_class(text):
    signals = []
    if re.search(r'\bclass\s+\w+\s*(?:extends|implements)\b', text, re.IGNORECASE):
        signals.append("class inheritance")
    if re.search(r'\b(interface|abstract class|base class|parent class)\b', text, re.IGNORECASE):
        signals.append("type hierarchy language")
    if re.search(r'\b(polymorphism|inheritance|encapsulation)\b', text, re.IGNORECASE):
        signals.append("OOP concepts")
    if re.search(r'\b(subclass|superclass|mixin|trait)\b', text, re.IGNORECASE):
        signals.append("class relationship")
    # Chinese
    if re.search(r'(类|接口|抽象类|多态|继承|封装)', text):
        signals.append(label("Chinese class terms", "类相关术语"))
    return signals

def detect_timeline(text):
    signals = []
    if re.search(r'\b(timeline|chronolog|over time|history of)\b', text, re.IGNORECASE):
        signals.append("timeline language")
    date_refs = re.findall(r'\b(20\d{2}|Q[1-4]|January|February|March|April|May|June|July|August|September|October|November|December)\b', text, re.IGNORECASE)
    if len(date_refs) >= 2:
        signals.append(f"multiple dates ({', '.join(date_refs[:3])})")
    if re.search(r'\b(v\d+|version\s+\d+|release\s+\d+)\b', text, re.IGNORECASE):
        versions = re.findall(r'\b(v\d+[\.\d]*|version\s+\d+[\.\d]*)\b', text, re.IGNORECASE)
        if len(versions) >= 2:
            signals.append(f"version progression ({', '.join(versions[:3])})")
    if re.search(r'\b(milestone|roadmap|evolution|progression)\b', text, re.IGNORECASE):
        signals.append("progression language")
    # Chinese
    if re.search(r'(时间线|历程|版本演进|里程碑|路线图)', text):
        signals.append(label("Chinese timeline terms", "时间线相关术语"))
    return signals


# --- Mermaid generators ---

def gen_architecture_mermaid(text):
    components = re.findall(
        r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)?)\b', text)
    skip = {'The','This','That','Each','For','And','But','With','When','How',
            'What','Where','Its','Our','All','Any','Some','Most','These','Those'}
    named = []
    for c in components:
        if c not in skip and c not in named and len(c) > 2:
            named.append(c)
    if len(named) < 2:
        named = ["Service A", "Service B", "Database"]
    named = named[:6]
    lines = ["graph TD"]
    for i, name in enumerate(named):
        nid = chr(65 + i)
        lines.append(f'    {nid}["{name}"]')
    for i in range(len(named) - 1):
        lines.append(f'    {chr(65+i)} --> {chr(65+i+1)}')
    return '\n'.join(lines)

def gen_flowchart_mermaid(text):
    ordered = re.findall(r'^\d+\.\s+(.+)', text, re.MULTILINE)
    if ordered:
        steps = [s.strip()[:40] for s in ordered[:6]]
    else:
        sentences = re.split(r'[.!?]\s+', text)
        steps = []
        for s in sentences:
            if re.search(r'\b(first|then|next|finally|start|begin|after)\b', s, re.IGNORECASE) and len(s) > 10:
                steps.append(s.strip()[:40])
        if not steps:
            steps = ["Step 1", "Step 2", "Step 3"]
    if len(steps) < 2:
        steps = ["Start", "Process", "End"]
    lines = ["flowchart TD"]
    for i, step in enumerate(steps):
        nid = chr(65 + i) if i < 26 else f"N{i}"
        safe = step.replace('"', "'").replace('[', '(').replace(']', ')')
        lines.append(f'    {nid}["{safe}"]')
    for i in range(len(steps) - 1):
        a = chr(65 + i) if i < 26 else f"N{i}"
        b = chr(65 + i + 1) if (i + 1) < 26 else f"N{i+1}"
        lines.append(f'    {a} --> {b}')
    return '\n'.join(lines)

def gen_state_mermaid(text):
    state_words = re.findall(
        r'\b(pending|active|inactive|completed|failed|cancelled|archived|'
        r'draft|published|approved|rejected|idle|running|stopped|paused|'
        r'error|ready|waiting|processing|done|created|deleted|open|closed)\b',
        text, re.IGNORECASE)
    unique = list(dict.fromkeys(s.capitalize() for s in state_words))
    if len(unique) < 2:
        unique = ["State1", "State2", "State3"]
    unique = unique[:6]
    lines = ["stateDiagram-v2"]
    lines.append(f"    [*] --> {unique[0]}")
    for i in range(len(unique) - 1):
        lines.append(f"    {unique[i]} --> {unique[i+1]}")
    lines.append(f"    {unique[-1]} --> [*]")
    return '\n'.join(lines)

def gen_sequence_mermaid(text):
    actors = []
    candidates = re.findall(
        r'\b(client|server|user|browser|api|database|service|gateway|'
        r'proxy|auth|cache)\b', text, re.IGNORECASE)
    for a in candidates:
        cap = a.capitalize()
        if cap not in actors:
            actors.append(cap)
    if len(actors) < 2:
        actors = ["Client", "Server"]
    actors = actors[:4]
    lines = ["sequenceDiagram"]
    for i in range(len(actors) - 1):
        lines.append(f"    {actors[i]}->>+{actors[i+1]}: Request")
        lines.append(f"    {actors[i+1]}-->>-{actors[i]}: Response")
    return '\n'.join(lines)

def gen_er_mermaid(text):
    tables = re.findall(r'\b([A-Z][a-zA-Z]*)\s+(?:table|entity|model)\b', text, re.IGNORECASE)
    if not tables:
        tables = re.findall(r'\b(?:table|entity|model)\s+([A-Z][a-zA-Z]*)\b', text, re.IGNORECASE)
    tables = list(dict.fromkeys(t.upper() for t in tables))[:4]
    if len(tables) < 2:
        tables = ["ENTITY_A", "ENTITY_B", "ENTITY_C"]
    lines = ["erDiagram"]
    for i in range(len(tables) - 1):
        lines.append(f'    {tables[i]} ||--o{{ {tables[i+1]} : "has"')
    return '\n'.join(lines)

def gen_class_mermaid(text):
    classes = re.findall(r'\bclass\s+(\w+)', text, re.IGNORECASE)
    classes = list(dict.fromkeys(classes))[:4]
    if len(classes) < 2:
        classes = ["BaseClass", "ChildClass"]
    lines = ["classDiagram"]
    for c in classes:
        lines.append(f"    class {c}")
    if len(classes) >= 2:
        lines.append(f"    {classes[0]} <|-- {classes[1]}")
    return '\n'.join(lines)

def gen_timeline_mermaid(text):
    dates = re.findall(r'\b(20\d{2}(?:-\d{2})?|Q[1-4]\s*20\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})\b', text, re.IGNORECASE)
    versions = re.findall(r'\b(v\d+[\.\d]*)\b', text, re.IGNORECASE)
    items = dates[:4] or versions[:4] or ["Phase 1", "Phase 2", "Phase 3"]
    # Use a gantt as timeline proxy (mermaid doesn't have a native timeline)
    lines = ["gantt"]
    lines.append("    title Timeline")
    lines.append("    dateFormat YYYY")
    for i, item in enumerate(items):
        lines.append(f"    {item} : t{i}, 2024, 1y")
    return '\n'.join(lines)


# --- Main analysis ---

suggestions = []

for section in sections:
    heading = section["heading"]
    raw_text = section["content"]

    # Skip very short sections
    stripped = re.sub(r'\s+', ' ', raw_text).strip()
    if len(stripped) < 30:
        continue

    prose = strip_code_blocks(raw_text)
    loc = heading if heading != "(intro)" else label("(Introduction)", "(引言)")

    # Architecture
    sigs = detect_architecture(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "architecture",
            "description": label(
                f"Architecture diagram showing system components and their relationships",
                f"架构图：展示系统组件及其关系"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_architecture_mermaid(prose)
        })

    # Flowchart
    sigs = detect_flowchart(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "flowchart",
            "description": label(
                f"Flowchart showing the step-by-step process",
                f"流程图：展示分步过程"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_flowchart_mermaid(prose)
        })

    # Comparison
    sigs = detect_comparison(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "comparison_table",
            "description": label(
                f"Comparison table highlighting differences between approaches",
                f"对比表：突出不同方案之间的差异"),
            "rationale": "; ".join(sigs),
            "mermaid": None
        })

    # State
    sigs = detect_state(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "state",
            "description": label(
                f"State diagram showing transitions between states",
                f"状态图：展示状态之间的转换"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_state_mermaid(prose)
        })

    # Sequence
    sigs = detect_sequence(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "sequence",
            "description": label(
                f"Sequence diagram showing interaction between components",
                f"时序图：展示组件之间的交互"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_sequence_mermaid(prose)
        })

    # Entity-Relationship
    sigs = detect_er(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "er",
            "description": label(
                f"Entity-relationship diagram showing data model",
                f"ER图：展示数据模型关系"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_er_mermaid(prose)
        })

    # Class
    sigs = detect_class(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "class",
            "description": label(
                f"Class diagram showing type hierarchy and relationships",
                f"类图：展示类型层级和关系"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_class_mermaid(prose)
        })

    # Timeline
    sigs = detect_timeline(prose)
    if sigs:
        suggestions.append({
            "location": loc,
            "line": section["start_line"],
            "type": "timeline",
            "description": label(
                f"Timeline showing progression or chronology",
                f"时间线：展示进展或时间顺序"),
            "rationale": "; ".join(sigs),
            "mermaid": gen_timeline_mermaid(prose)
        })

# --- Summary ---
type_counts = {}
for s in suggestions:
    t = s["type"]
    type_counts[t] = type_counts.get(t, 0) + 1

result = {
    "suggestions": suggestions,
    "summary": {
        "total": len(suggestions),
        "type_breakdown": type_counts,
        "language_detected": "zh" if is_chinese else "en"
    }
}

# --- Output ---
if verbose:
    print(f"\n{'='*50}")
    print(label(
        f"Diagram Suggestions: {len(suggestions)} found",
        f"图表建议：找到 {len(suggestions)} 个"))
    print(f"{'='*50}")
    for i, s in enumerate(suggestions, 1):
        print(f"\n--- {label('Suggestion', '建议')} {i} ---")
        print(f"{label('Location:', '位置：')} {s['location']} (line {s['line']})")
        print(f"{label('Type:', '类型：')} {s['type']}")
        print(f"{label('Description:', '描述：')} {s['description']}")
        if s.get('mermaid'):
            print(f"\n{label('Mermaid:', 'Mermaid语法：')}")
            print("```mermaid")
            print(s['mermaid'])
            print("```")
    print(f"\n{label('Type breakdown:', '类型分布：')}")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
else:
    print(json.dumps(result))

# --- Atomic write to state dir ---
if state_dir and os.path.isdir(state_dir):
    tmp_file = os.path.join(state_dir, "diagram-suggestions.json.tmp." + str(os.getpid()))
    target_file = os.path.join(state_dir, "diagram-suggestions.json")
    with open(tmp_file, "w") as f:
        json.dump(result, f, indent=2)
    os.rename(tmp_file, target_file)
PYEOF
