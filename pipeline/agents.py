"""Multi-agent orchestration for intelligent content processing.

Runs parallel agents for:
  - Semantic filtering (glossary + keyword matching)
  - Intelligent ranking (multi-criteria scoring)
  - Insight generation (cross-source clustering)
  - Domain extraction (tech-specific content detection)
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("agents")


class Agent:
    """Base agent for processing content."""
    def __init__(self, name: str):
        self.name = name

    def process(self, items: list[dict], context: dict) -> list[dict]:
        """Process items and return modified items."""
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"


class SemanticFilterAgent(Agent):
    """Filters items by semantic relevance using glossary and keywords."""

    def __init__(self, glossary: dict, profile_keywords: list[str]):
        super().__init__("semantic_filter")
        self.glossary = glossary
        self.keywords = [k.lower() for k in profile_keywords]

    def process(self, items: list[dict], context: dict) -> list[dict]:
        """Score items by relevance to user interests."""
        scored = []

        for item in items:
            score = self._calculate_relevance(item)
            item["_semantic_score"] = score
            if score > 0:  # Keep items with any relevance
                scored.append(item)

        scored.sort(key=lambda x: x["_semantic_score"], reverse=True)
        return scored

    def _calculate_relevance(self, item: dict) -> float:
        """Calculate relevance score 0.0-1.0."""
        text = f"{item.get('title', '')} {item.get('body', '')}".lower()

        # Keyword matching (max 1.0)
        keyword_matches = sum(1 for k in self.keywords if k in text)
        keyword_score = min(keyword_matches / max(len(self.keywords), 1), 1.0)

        # Glossary term matching (max 0.5 boost)
        glossary_terms = [g["t"].lower() for g in self.glossary.values() if "t" in g]
        glossary_matches = sum(1 for t in glossary_terms if t in text)
        glossary_score = min(glossary_matches / max(len(glossary_terms), 1), 0.5)

        return keyword_score + glossary_score


class RankingAgent(Agent):
    """Ranks items by multiple criteria: recency, relevance, domain match."""

    def __init__(self, domain_keywords: dict[str, list[str]]):
        super().__init__("ranking")
        self.domain_keywords = {k: [w.lower() for w in v] for k, v in domain_keywords.items()}

    def process(self, items: list[dict], context: dict) -> list[dict]:
        """Score and rank items."""
        scored = []

        for item in items:
            recency = self._recency_score(item.get("published_at"))
            semantic = item.get("_semantic_score", 0.0)
            domain = self._domain_specificity_score(item)

            # Weighted scoring: 40% recency, 35% semantic, 25% domain
            total_score = (recency * 0.4) + (semantic * 0.35) + (domain * 0.25)
            item["_rank_score"] = round(total_score, 4)
            scored.append(item)

        scored.sort(key=lambda x: x["_rank_score"], reverse=True)
        return scored

    def _recency_score(self, published_at: Optional[str]) -> float:
        """Score based on age (exponential decay)."""
        if not published_at:
            return 0.5

        try:
            pub = datetime.fromisoformat(published_at)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
            if age_hours < 0:
                age_hours = 0
            # Half-life of 36 hours
            return 0.5 ** (age_hours / 36)
        except Exception:
            return 0.5

    def _domain_specificity_score(self, item: dict) -> float:
        """Score higher if content matches technical domains."""
        text = f"{item.get('title', '')} {item.get('body', '')}".lower()
        domain_matches = 0

        for domain, keywords in self.domain_keywords.items():
            domain_matches += sum(1 for kw in keywords if kw in text)

        return min(domain_matches / 5.0, 1.0)  # Max score at 5+ domain keywords


class InsightAgent(Agent):
    """Generates insights by clustering related articles across sources."""

    def __init__(self):
        super().__init__("insights")
        self.similarity_threshold = 0.3

    def process(self, items: list[dict], context: dict) -> list[dict]:
        """Generate insights from item clustering."""
        if len(items) < 2:
            return items

        # Cluster similar articles
        clusters = self._cluster_by_similarity(items)

        # Generate insight items for clusters with 2+ articles
        insights = []
        for cluster in clusters:
            if len(cluster) >= 2:
                insight = self._generate_insight(cluster)
                insights.append(insight)

        # Tag original items with cluster info
        for i, item in enumerate(items):
            for cid, cluster in enumerate(clusters):
                if item in cluster:
                    item["_cluster_id"] = cid
                    break

        return items + insights

    def _cluster_by_similarity(self, items: list[dict]) -> list[list[dict]]:
        """Cluster articles by title/topic similarity."""
        from difflib import SequenceMatcher

        clusters = []
        used = set()

        for i, item1 in enumerate(items):
            if i in used:
                continue

            cluster = [item1]
            used.add(i)
            title1 = item1.get("title", "").lower()

            for j, item2 in enumerate(items[i + 1:], start=i + 1):
                if j in used:
                    continue

                title2 = item2.get("title", "").lower()
                similarity = SequenceMatcher(None, title1, title2).ratio()

                if similarity > self.similarity_threshold:
                    cluster.append(item2)
                    used.add(j)

            clusters.append(cluster)

        return clusters

    def _generate_insight(self, cluster: list[dict]) -> dict:
        """Generate a meta-item representing a cluster insight."""
        titles = [i.get("title", "") for i in cluster]
        sources = [i.get("source", "") for i in cluster]

        # Find common keywords
        words = " ".join(titles).lower().split()
        common = Counter(words).most_common(3)
        topic = " ".join([w for w, _ in common if len(w) > 3])

        return {
            "title": f"📌 Trending: {topic or 'Multiple sources'}",
            "body": f"{len(cluster)} sources reporting on this topic",
            "source": "insight",
            "url": "",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "_is_insight": True,
            "_cluster_sources": list(set(sources)),
        }


class DomainExtractionAgent(Agent):
    """Extracts and highlights domain-specific technical content."""

    def __init__(self, domains: dict[str, dict]):
        super().__init__("domain_extraction")
        self.domains = domains  # e.g., {"istqb": {"keywords": [...], "boost": 1.5}}

    def process(self, items: list[dict], context: dict) -> list[dict]:
        """Tag and boost domain-specific items."""
        for item in items:
            domain_tags = self._extract_domains(item)
            item["_domain_tags"] = domain_tags
            if domain_tags:
                # Boost rank score for domain-specific content
                current_score = item.get("_rank_score", 0.5)
                boost_factor = 1.0 + (len(domain_tags) * 0.2)  # +20% per domain match
                item["_rank_score"] = round(current_score * boost_factor, 4)

        return items

    def _extract_domains(self, item: dict) -> list[str]:
        """Identify which domains this item relates to."""
        text = f"{item.get('title', '')} {item.get('body', '')}".lower()
        matched_domains = []

        for domain, config in self.domains.items():
            keywords = [kw.lower() for kw in config.get("keywords", [])]
            if any(kw in text for kw in keywords):
                matched_domains.append(domain)

        return matched_domains


class AgentOrchestrator:
    """Runs multiple agents in parallel for efficient content processing."""

    def __init__(self):
        self.agents: list[Agent] = []

    def add_agent(self, agent: Agent) -> None:
        self.agents.append(agent)

    def process(self, items: list[dict], context: dict = None) -> list[dict]:
        """Run all agents in sequence, passing results forward."""
        context = context or {}
        current = items

        for agent in self.agents:
            log.info(f"Running agent: {agent.name}")
            current = agent.process(current, context)

        # Final sort by rank score
        current.sort(key=lambda x: x.get("_rank_score", 0), reverse=True)
        return current


def create_default_orchestrator(glossary: dict, profile: dict, domain_keywords: dict) -> AgentOrchestrator:
    """Create orchestrator with standard agents for briefing."""
    orchestrator = AgentOrchestrator()

    # Extract keywords from profile
    keywords = []
    if "technical_interests" in profile:
        keywords.extend(profile["technical_interests"])
    if "profession" in profile:
        keywords.append(profile["profession"])

    orchestrator.add_agent(SemanticFilterAgent(glossary, keywords))
    orchestrator.add_agent(RankingAgent(domain_keywords))
    orchestrator.add_agent(InsightAgent())
    orchestrator.add_agent(DomainExtractionAgent(domain_keywords))

    return orchestrator
