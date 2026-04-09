#!/usr/bin/env python3
"""Topic research — generates research questions, competitive landscape queries,
unique angles, and a research brief template from a topic string.
Usage: topic_research.py <project_dir> <topic>
"""

import hashlib
import json
import os
import re
import sys

from utils import atomic_json_write, read_json_file, timestamp_now


def usage():
    print("""Usage: topic_research.py <project_dir> <topic>

Generates research questions, competitive landscape search queries,
unique angles, and a structured research brief from a topic string.

Creates .essay-state/ if it doesn't exist.

Reads: pipeline-state.json, materials.json
Writes: research-brief.json

Output: JSON brief to stdout""")


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    topic = sys.argv[2] if len(sys.argv) > 2 else ""

    if not project_dir or not topic:
        print("ERROR: project_dir and topic required", file=sys.stderr)
        print("Usage: topic_research.py <project_dir> <topic>", file=sys.stderr)
        sys.exit(1)

    state_dir = os.path.join(project_dir, ".essay-state")
    os.makedirs(state_dir, exist_ok=True)

    # --- Read existing state if available ---

    pipeline_file = os.path.join(state_dir, "pipeline-state.json")
    materials_file = os.path.join(state_dir, "materials.json")

    pipeline = read_json_file(pipeline_file)
    materials = read_json_file(materials_file)

    # --- Keyword extraction ---

    def extract_keywords(text):
        """Extract meaningful keywords from the topic string."""
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can", "need", "dare",
            "about", "above", "after", "again", "all", "also", "am", "any",
            "because", "before", "between", "both", "each", "few", "how",
            "if", "into", "it", "its", "just", "more", "most", "no", "nor",
            "not", "only", "other", "our", "out", "over", "own", "same",
            "so", "some", "such", "than", "that", "their", "them", "then",
            "there", "these", "they", "this", "those", "through", "too",
            "under", "until", "up", "very", "what", "when", "where", "which",
            "while", "who", "whom", "why", "you", "your", "vs", "using",
        }
        tokens = re.split(r'[^a-zA-Z0-9\-\+#\.]+', text)
        keywords = []
        for token in tokens:
            clean = token.strip("-. ")
            if clean and clean.lower() not in stop_words and len(clean) > 1:
                keywords.append(clean)
        return keywords

    keywords = extract_keywords(topic)
    topic_lower = topic.lower()

    # Deterministic seed for stable output
    seed_str = topic
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)

    def pick(lst, offset=0):
        """Pick an item deterministically from a list."""
        if not lst:
            return ""
        return lst[(seed + offset) % len(lst)]

    # --- Detect topic domain ---

    domain_signals = {
        "frontend": ["react", "vue", "angular", "svelte", "css", "html", "javascript",
                      "typescript", "nextjs", "next.js", "remix", "tailwind", "ui", "ux",
                      "component", "dom", "browser", "web", "frontend", "front-end"],
        "backend": ["api", "rest", "graphql", "grpc", "server", "backend", "back-end",
                    "node", "express", "fastapi", "django", "flask", "spring", "rails",
                    "microservice", "monolith", "endpoint"],
        "devops": ["kubernetes", "k8s", "docker", "ci/cd", "cicd", "pipeline", "deploy",
                   "terraform", "ansible", "helm", "gitops", "infrastructure", "iac",
                   "monitoring", "observability", "sre", "devops"],
        "data": ["database", "sql", "nosql", "postgresql", "postgres", "mysql", "mongo",
                 "redis", "elasticsearch", "data", "etl", "warehouse", "lake", "analytics",
                 "bigquery", "spark", "kafka", "streaming"],
        "ai_ml": ["machine learning", "ml", "ai", "deep learning", "neural", "llm",
                  "gpt", "transformer", "nlp", "computer vision", "model", "training",
                  "inference", "fine-tuning", "rag", "embedding", "vector"],
        "security": ["security", "auth", "authentication", "authorization", "oauth",
                     "jwt", "encryption", "vulnerability", "penetration", "zero-trust",
                     "sso", "rbac", "csrf", "xss", "injection"],
        "architecture": ["architecture", "design pattern", "microservice", "monolith",
                         "event-driven", "event sourcing", "cqrs", "ddd", "domain-driven",
                         "clean architecture", "hexagonal", "distributed", "scalability"],
        "testing": ["testing", "test", "tdd", "bdd", "unit test", "integration test",
                    "e2e", "playwright", "cypress", "jest", "pytest", "quality",
                    "coverage", "mutation testing"],
        "mobile": ["mobile", "ios", "android", "react native", "flutter", "swift",
                   "kotlin", "expo", "app"],
        "cloud": ["aws", "azure", "gcp", "cloud", "serverless", "lambda", "function",
                  "s3", "cdn", "edge", "cloudflare"],
    }

    detected_domains = []
    for domain, signals in domain_signals.items():
        for signal in signals:
            if signal in topic_lower:
                if domain not in detected_domains:
                    detected_domains.append(domain)
                break

    if not detected_domains:
        detected_domains = ["general"]

    # --- Generate research questions ---

    def generate_research_questions():
        """Generate targeted research questions across multiple dimensions."""
        questions = []

        questions.append({
            "category": "foundational",
            "question": f"What are the core concepts and principles behind {topic}?",
            "purpose": "Establish baseline knowledge and terminology"
        })

        questions.append({
            "category": "state_of_art",
            "question": f"What is the current state of {topic} in 2024-2025? What recent developments have changed the landscape?",
            "purpose": "Ensure the essay reflects current reality, not outdated information"
        })

        questions.append({
            "category": "pain_points",
            "question": f"What are the most common challenges and frustrations engineers face with {topic}?",
            "purpose": "Identify reader pain points to address directly"
        })

        questions.append({
            "category": "conventional_wisdom",
            "question": f"What does the conventional wisdom say about {topic}, and where might it be wrong or incomplete?",
            "purpose": "Find contrarian or nuanced angles that differentiate the essay"
        })

        questions.append({
            "category": "case_studies",
            "question": f"What notable companies or projects have successfully implemented {topic}? What were their specific approaches and outcomes?",
            "purpose": "Provide concrete examples and social proof"
        })

        questions.append({
            "category": "trade_offs",
            "question": f"What are the key trade-offs and limitations when adopting {topic}? When is it NOT the right choice?",
            "purpose": "Add nuance and credibility by acknowledging downsides"
        })

        questions.append({
            "category": "alternatives",
            "question": f"What are the main alternatives to {topic}, and how do they compare on key dimensions (performance, complexity, cost, learning curve)?",
            "purpose": "Position the topic within the broader ecosystem"
        })

        questions.append({
            "category": "implementation",
            "question": f"What does a practical step-by-step implementation of {topic} look like? What are the critical first steps?",
            "purpose": "Provide actionable guidance the reader can follow"
        })

        questions.append({
            "category": "mistakes",
            "question": f"What are the most common mistakes or anti-patterns when working with {topic}?",
            "purpose": "Help readers avoid known pitfalls"
        })

        questions.append({
            "category": "future",
            "question": f"Where is {topic} heading in the next 2-3 years? What emerging trends will shape its evolution?",
            "purpose": "Add forward-looking perspective and lasting relevance"
        })

        questions.append({
            "category": "metrics",
            "question": f"How do you measure success with {topic}? What KPIs or benchmarks indicate you're doing it well?",
            "purpose": "Give readers concrete ways to evaluate their own progress"
        })

        # Domain-specific question
        if "ai_ml" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"What are the ethical considerations and bias risks associated with {topic}?",
                "purpose": "Address AI/ML-specific concerns that readers care about"
            })
        elif "security" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"What are the most recent vulnerability patterns and attack vectors related to {topic}?",
                "purpose": "Address security-specific threat landscape"
            })
        elif "devops" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"How does {topic} integrate with existing CI/CD pipelines and infrastructure-as-code workflows?",
                "purpose": "Address practical devops integration concerns"
            })
        elif "data" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"How does {topic} handle data consistency, durability, and recovery at scale?",
                "purpose": "Address data reliability concerns"
            })
        elif "frontend" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"How does {topic} impact Core Web Vitals, accessibility, and user experience metrics?",
                "purpose": "Address frontend performance and UX concerns"
            })
        elif "architecture" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"How does {topic} evolve as the system grows from startup to enterprise scale?",
                "purpose": "Address scalability and evolution concerns"
            })
        elif "testing" in detected_domains:
            questions.append({
                "category": "domain_specific",
                "question": f"What is the optimal test pyramid or testing strategy shape for {topic}?",
                "purpose": "Address testing strategy concerns"
            })
        else:
            questions.append({
                "category": "domain_specific",
                "question": f"What skills or background knowledge does a team need to adopt {topic} effectively?",
                "purpose": "Address adoption readiness"
            })

        return questions

    # --- Generate competitive landscape search queries ---

    def generate_search_queries():
        """Generate search queries to map the competitive content landscape."""
        queries = []

        queries.append({
            "query": f'"{topic}" best practices site:dev.to OR site:medium.com',
            "purpose": "Find popular developer community articles",
            "target": "dev_community"
        })
        queries.append({
            "query": f'"{topic}" guide OR tutorial site:github.com',
            "purpose": "Find GitHub-based guides and documentation",
            "target": "github"
        })
        queries.append({
            "query": f'"{topic}" engineering blog',
            "purpose": "Find company engineering blog posts",
            "target": "eng_blogs"
        })

        if keywords:
            kw_joined = " ".join(keywords[:3])
            queries.append({
                "query": f"{kw_joined} real-world experience lessons learned",
                "purpose": "Find experience reports and retrospectives",
                "target": "experience_reports"
            })
            queries.append({
                "query": f"{kw_joined} comparison vs alternative",
                "purpose": "Find comparison and alternatives content",
                "target": "comparisons"
            })

        queries.append({
            "query": f'"{topic}" site:news.ycombinator.com',
            "purpose": "Find Hacker News discussions for community sentiment",
            "target": "hacker_news"
        })
        queries.append({
            "query": f'"{topic}" site:reddit.com/r/programming OR site:reddit.com/r/webdev OR site:reddit.com/r/devops',
            "purpose": "Find Reddit discussions and pain points",
            "target": "reddit"
        })

        queries.append({
            "query": f'"{topic}" whitepaper OR research paper OR case study',
            "purpose": "Find authoritative deep-dive content",
            "target": "academic"
        })

        queries.append({
            "query": f'"{topic}" conference talk OR presentation site:youtube.com',
            "purpose": "Find conference talks and video content",
            "target": "video"
        })

        queries.append({
            "query": f'"{topic}" 2024 OR 2025',
            "purpose": "Find recent content to gauge current coverage",
            "target": "recent"
        })

        return queries

    # --- Identify unique angles ---

    def identify_unique_angles():
        """Suggest unique angles based on topic keywords and domain."""
        angles = []

        angles.append({
            "angle": f"The case against {topic}: when simpler alternatives win",
            "type": "contrarian",
            "strength": "High engagement from debate and disagreement",
            "risk": "May alienate true believers; requires strong evidence"
        })

        angles.append({
            "angle": f"Lessons from migrating to {topic} in production",
            "type": "experience_report",
            "strength": "Authentic, hard-to-replicate, builds trust",
            "risk": "Requires real experience or detailed case study research"
        })

        angles.append({
            "angle": f"The hidden costs of {topic} nobody talks about",
            "type": "hidden_complexity",
            "strength": "Curiosity gap + practical value for decision-makers",
            "risk": "Can come across as negative if not balanced"
        })

        angles.append({
            "angle": f"A decision framework for when to use {topic}",
            "type": "decision_framework",
            "strength": "Evergreen, practical, high bookmark rate",
            "risk": "Needs rigorous criteria to be credible"
        })

        angles.append({
            "angle": f"{topic}: the gap between tutorials and production",
            "type": "bridge",
            "strength": "Addresses a real frustration for intermediate developers",
            "risk": "Must deliver genuinely advanced insights, not rehashed basics"
        })

        # Domain-specific angles
        if "ai_ml" in detected_domains:
            angles.append({
                "angle": f"Building {topic} that actually works: beyond the demo",
                "type": "domain_practical",
                "strength": "Cuts through AI hype with production reality",
                "risk": "Fast-moving field; may date quickly"
            })
        elif "devops" in detected_domains:
            angles.append({
                "angle": f"From zero to production {topic} in a weekend",
                "type": "domain_practical",
                "strength": "Concrete timeline creates urgency and clarity",
                "risk": "Oversimplification risk for complex topics"
            })
        elif "architecture" in detected_domains:
            angles.append({
                "angle": f"How {topic} decisions compound: a 3-year retrospective",
                "type": "domain_practical",
                "strength": "Long-term perspective is rare and valuable",
                "risk": "Requires longitudinal evidence"
            })
        elif "security" in detected_domains:
            angles.append({
                "angle": f"The {topic} mistakes that led to real breaches",
                "type": "domain_practical",
                "strength": "Urgency and concrete consequences drive attention",
                "risk": "Must cite real incidents responsibly"
            })
        elif "frontend" in detected_domains:
            angles.append({
                "angle": f"Why your {topic} implementation is slower than you think",
                "type": "domain_practical",
                "strength": "Performance is always a hot topic in frontend",
                "risk": "Need real benchmarks to be credible"
            })
        elif "data" in detected_domains:
            angles.append({
                "angle": f"{topic} at scale: what changes when you hit 10x growth",
                "type": "domain_practical",
                "strength": "Scale stories are compelling for growing teams",
                "risk": "Need specific numbers and evidence"
            })
        elif "testing" in detected_domains:
            angles.append({
                "angle": f"How {topic} changed our bug escape rate by 80%",
                "type": "domain_practical",
                "strength": "Concrete metrics make testing arguments persuasive",
                "risk": "Results must be believable and reproducible"
            })
        else:
            angles.append({
                "angle": f"What I wish I knew before starting with {topic}",
                "type": "domain_practical",
                "strength": "Relatable, saves reader time and mistakes",
                "risk": "Must go beyond surface-level advice"
            })

        # Cross-pollination angle
        if len(detected_domains) > 1:
            d1 = detected_domains[0]
            d2 = detected_domains[1]
            angles.append({
                "angle": f"Applying {d1} principles to {d2}: lessons from {topic}",
                "type": "cross_domain",
                "strength": "Novel perspective from combining domains",
                "risk": "Analogy may not hold under scrutiny"
            })
        else:
            adjacent_map = {
                "frontend": "backend",
                "backend": "frontend",
                "devops": "architecture",
                "data": "ai_ml",
                "ai_ml": "data",
                "security": "devops",
                "architecture": "devops",
                "testing": "architecture",
                "mobile": "frontend",
                "cloud": "devops",
                "general": "architecture",
            }
            primary = detected_domains[0]
            adjacent = adjacent_map.get(primary, "architecture")
            angles.append({
                "angle": f"What {adjacent} engineers can teach us about {topic}",
                "type": "cross_domain",
                "strength": "Fresh perspective from an adjacent discipline",
                "risk": "Must genuinely connect the domains"
            })

        angles.append({
            "angle": f"5 myths about {topic} that are costing your team",
            "type": "myth_busting",
            "strength": "Numbered myths create structure and shareability",
            "risk": "Myths must be genuinely believed by the audience"
        })

        return angles

    # --- Build the research brief ---

    research_questions = generate_research_questions()
    search_queries = generate_search_queries()
    unique_angles = identify_unique_angles()

    # Score angles based on topic characteristics
    for angle_entry in unique_angles:
        score = 5.0
        a_type = angle_entry["type"]

        if a_type == "experience_report" and any(d in detected_domains for d in ["devops", "backend", "data"]):
            score += 1.5
        if a_type == "contrarian" and len(keywords) <= 2:
            score += 1.0
        if a_type == "decision_framework" and "architecture" in detected_domains:
            score += 1.5
        if a_type == "bridge" and any(d in detected_domains for d in ["frontend", "mobile"]):
            score += 1.0
        if a_type == "domain_practical":
            score += 1.0
        if a_type == "cross_domain" and len(detected_domains) > 1:
            score += 1.5
        if a_type == "myth_busting" and len(keywords) <= 3:
            score += 0.5

        angle_entry["relevance_score"] = round(max(1, min(10, score)), 1)

    # Sort angles by relevance score descending
    unique_angles.sort(key=lambda x: -x["relevance_score"])

    # Assign ranks
    for i, angle_entry in enumerate(unique_angles):
        angle_entry["rank"] = i + 1

    # Categorize research questions by priority
    priority_categories = {
        "high": ["pain_points", "conventional_wisdom", "case_studies", "mistakes"],
        "medium": ["state_of_art", "trade_offs", "alternatives", "implementation"],
        "low": ["foundational", "future", "metrics", "domain_specific"],
    }

    for q in research_questions:
        cat = q["category"]
        if cat in priority_categories["high"]:
            q["priority"] = "high"
        elif cat in priority_categories["medium"]:
            q["priority"] = "medium"
        else:
            q["priority"] = "low"

    # Build timestamp
    now = timestamp_now()

    # Assemble the research brief
    brief = {
        "topic": topic,
        "keywords": keywords,
        "detected_domains": detected_domains,
        "generated_at": now,
        "research_questions": research_questions,
        "search_queries": search_queries,
        "unique_angles": unique_angles,
        "summary": {
            "total_questions": len(research_questions),
            "total_search_queries": len(search_queries),
            "total_angles": len(unique_angles),
            "high_priority_questions": len([q for q in research_questions if q["priority"] == "high"]),
            "top_angle": unique_angles[0]["angle"] if unique_angles else "",
            "top_angle_type": unique_angles[0]["type"] if unique_angles else "",
        },
        "inputs_used": {
            "pipeline_state": os.path.exists(pipeline_file),
            "materials": os.path.exists(materials_file),
        },
    }

    # Print to stdout
    print(json.dumps(brief, indent=2))

    # Atomic write to state directory
    os.makedirs(state_dir, exist_ok=True)
    target_file = os.path.join(state_dir, "research-brief.json")
    atomic_json_write(target_file, brief)


if __name__ == "__main__":
    main()
