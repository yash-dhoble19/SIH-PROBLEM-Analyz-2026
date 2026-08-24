"""
Agent 4: SIH Matching Agent with Explicit Intent Alignment Guard & Full-Corpus Triage.
Performs full-corpus parallel Groq triage unioned with pgvector semantic retrieval,
explicit intent/domain alignment veto, and 6-factor multi-dimensional scoring against the structured Capability Manifest.
"""

import json
import logging
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Set, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from platform_core.agents.base import BaseAgent
from platform_core.ai.embeddings import EmbeddingProvider
from platform_core.ai.providers import HeuristicAIProvider
from platform_core.database.models import ProblemStatement

logger = logging.getLogger("sih_platform.agents.matching")


class SIHMatchingAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 4: SIH Matching Agent", ai_provider)
        self.embedder = EmbeddingProvider()

    def assess_intent_alignment(self, repo_profile: Dict[str, Any], problem_statement: Any) -> Dict[str, Any]:
        """
        Assesses whether the repository's real-world purpose aligns with the SIH problem statement's core ask.
        Runs a structured evaluation and can veto candidates regardless of technical/tag overlaps.
        """
        repo_name = repo_profile.get("repo_name", "Repository")
        repo_purpose = repo_profile.get("project_summary") or repo_profile.get("description") or "Software Project"
        repo_features = ", ".join(repo_profile.get("core_features") or repo_profile.get("detected_features") or ["General functionality"])
        repo_domains = ", ".join(repo_profile.get("target_domains") or ["General Software"])

        ps_id = getattr(problem_statement, "id", problem_statement.get("id") if isinstance(problem_statement, dict) else "SIH Problem")
        ps_title = getattr(problem_statement, "title", problem_statement.get("title") if isinstance(problem_statement, dict) else "")
        ps_theme = getattr(problem_statement, "theme", problem_statement.get("theme") if isinstance(problem_statement, dict) else "")
        ps_org = getattr(problem_statement, "organization", problem_statement.get("organization") if isinstance(problem_statement, dict) else "")
        ps_bg = getattr(problem_statement, "background", problem_statement.get("background") if isinstance(problem_statement, dict) else "") or "N/A"
        ps_desc = getattr(problem_statement, "description", problem_statement.get("description") if isinstance(problem_statement, dict) else "")
        ps_sol = getattr(problem_statement, "expected_solution", problem_statement.get("expected_solution") if isinstance(problem_statement, dict) else "") or "N/A"

        # Fast Pre-filter: Check deterministic domain compatibility first
        heuristic_res = self._heuristic_intent_assessment(repo_profile, ps_id, ps_title, ps_theme, ps_desc, ps_sol, ps_bg)
        if not heuristic_res.get("domain_match", True) or heuristic_res.get("aim_alignment_score", 0) >= 80:
            return heuristic_res

        # Try LLM Provider for ambiguous edge cases
        if self.ai_provider and not isinstance(self.ai_provider, HeuristicAIProvider):
            try:
                prompt = f"""You are an expert AI software architect evaluating whether a user's GitHub repository matches a government hackathon (Smart India Hackathon 2026) problem statement.

CRITICAL INSTRUCTION:
"Two projects can share a programming language or an 'AI/ML' label while solving completely unrelated problems. Judge on WHAT PROBLEM IS BEING SOLVED, not on tech stack. If the repo's stated purpose and the problem statement's expected solution do not share the same real-world domain and goal, domain_match must be false regardless of any technical similarity."

REPOSITORY PROFILE:
- Repository Name: {repo_name}
- What this Project Actually Does (Stated Purpose): {repo_purpose}
- Core Features: {repo_features}
- Identified Real-World Domains: {repo_domains}

SIH PROBLEM STATEMENT:
- ID: {ps_id}
- Title: {ps_title}
- Theme: {ps_theme}
- Organization / Ministry: {ps_org}
- Core Ask / Problem Background: {ps_bg}
- Detailed Description: {ps_desc}
- Expected Solution: {ps_sol}

TASK:
Evaluate whether this repository's actual purpose and real-world goal match what the ministry is asking for.
Respond ONLY with a valid JSON object:
{{
  "solves_same_core_problem": true,
  "aim_alignment_score": 85.0,
  "domain_match": true,
  "reasoning": "2-3 sentences explaining why it is or is not a match based on real-world intent and problem scope"
}}"""
                system_prompt = (
                    "You are a strict, objective AI software architect evaluating hackathon problem-solution fit. "
                    "You must ruthlessly filter out false positives where projects share only programming language or AI tags."
                )
                res = self.ai_provider.generate_json(prompt, system_prompt=system_prompt)
                if isinstance(res, dict) and "aim_alignment_score" in res and "domain_match" in res:
                    return {
                        "solves_same_core_problem": bool(res.get("solves_same_core_problem", False)),
                        "aim_alignment_score": float(res.get("aim_alignment_score", 0.0)),
                        "domain_match": bool(res.get("domain_match", False)),
                        "reasoning": str(res.get("reasoning", ""))
                    }
            except Exception as e:
                logger.warning(f"LLM intent assessment failed for {ps_id}: {e}. Falling back to continuous semantic heuristic.")

        return heuristic_res

    def _heuristic_intent_assessment(
        self,
        repo_profile: Dict[str, Any],
        ps_id: str,
        ps_title: str,
        ps_theme: str,
        ps_desc: str,
        ps_sol: str,
        ps_bg: str
    ) -> Dict[str, Any]:
        """
        Deterministic intent evaluation comparing real-world problem domain clusters.
        Computes dynamic continuous scores without silent hardcoded constants.
        """
        repo_text = (
            f"{repo_profile.get('repo_name', '')} "
            f"{repo_profile.get('project_summary', '')} "
            f"{repo_profile.get('description', '')} "
            f"{' '.join(repo_profile.get('core_features') or [])} "
            f"{' '.join(repo_profile.get('target_domains') or [])} "
            f"{' '.join(repo_profile.get('domain_signals') or [])}"
        ).lower()

        ps_text = f"{ps_title} {ps_theme} {ps_desc} {ps_sol} {ps_bg}".lower()

        domain_clusters = {
            "education_edtech": {
                "keywords": ["education", "learning", "student", "teacher", "school", "curriculum", "exam", "quiz", "classroom", "edtech", "tutoring", "pedagogy", "roadmap", "mastery", "career coach", "skill gap", "competency", "career guidance", "upskilling", "study"],
                "label": "Smart Education & Skill Development",
                "themes": ["smart education", "education"]
            },
            "cyber_security": {
                "keywords": ["firewall", "vulnerability scan", "penetration testing", "encryption", "intrusion detection", "soc", "siem", "ddos", "packet inspection", "malware", "ransomware", "phishing attack", "threat signature", "zero-day", "cybercrime", "network defense"],
                "label": "Cybersecurity & Network Defense",
                "themes": ["blockchain & cybersecurity", "cybersecurity", "security"]
            },
            "productivity_notes": {
                "keywords": ["note", "notes", "journal", "habit tracker", "todo list", "diary", "reminder app", "personal organizer", "markdown notes", "bullet journal", "daily planner"],
                "label": "Personal Productivity & Note-Taking",
                "themes": ["miscellaneous"]
            },
            "healthcare_neuro": {
                "keywords": ["health", "medical", "disease", "patient", "eeg", "alzheimer", "dementia", "mental health", "hospital", "clinical", "biomedical", "diagnosis", "doctor", "cognitive", "neurology", "vital signs"],
                "label": "Healthcare & Biomedical Systems",
                "themes": ["medtech / biotech / healthtech", "healthcare"]
            },
            "disaster_gis": {
                "keywords": ["landslide", "disaster", "flood", "earthquake", "weather warning", "gis", "hazard map", "terrain slope", "cyclone", "avalanche", "satellite warning", "geospatial warning", "sensor stream"],
                "label": "Disaster Management & Geospatial Warning",
                "themes": ["disaster management", "gis"]
            },
            "supply_chain_logistics": {
                "keywords": ["supply chain", "logistics", "warehouse", "inventory", "shipping", "freight", "fleet", "consignment", "cargo", "route optimization", "delivery tracking", "demand forecast", "vessel chartering"],
                "label": "Supply Chain & Smart Logistics",
                "themes": ["transportation & logistics", "logistics"]
            },
            "agriculture_crops": {
                "keywords": ["agriculture", "crop", "farming", "soil moisture", "farmer", "irrigation", "pest detection", "harvest", "fertilizer", "yield estimation", "agritech", "horticulture", "paddy", "wheat"],
                "label": "Agriculture & Smart Farming",
                "themes": ["agriculture, foodtech & rural development", "agriculture"]
            },
            "legal_judiciary": {
                "keywords": ["legal", "court", "law", "case file", "bail", "judge", "justice", "advocate", "litigation", "statute", "tribunal", "police fir"],
                "label": "Legal Tech & Judicial Governance",
                "themes": ["smart automation", "miscellaneous"]
            }
        }

        # Count keyword hits in clusters
        repo_cluster_scores = {}
        for c_key, c_data in domain_clusters.items():
            hits = sum(1 for kw in c_data["keywords"] if kw in repo_text)
            if hits > 0:
                repo_cluster_scores[c_key] = hits

        ps_cluster_scores = {}
        for c_key, c_data in domain_clusters.items():
            hits = sum(1 for kw in c_data["keywords"] if kw in ps_text)
            if hits > 0:
                ps_cluster_scores[c_key] = hits

        top_repo_cluster = max(repo_cluster_scores.items(), key=lambda x: x[1])[0] if repo_cluster_scores else None
        top_ps_cluster = max(ps_cluster_scores.items(), key=lambda x: x[1])[0] if ps_cluster_scores else None

        # 1. Direct Theme Match Check with continuous scoring
        target_domains = [d.lower() for d in repo_profile.get("target_domains", [])]
        ps_theme_lower = ps_theme.lower()

        # Compute keyword overlap between repo text and problem statement
        repo_words = set(re.findall(r'\b[a-z]{4,}\b', repo_text))
        ps_words = set(re.findall(r'\b[a-z]{4,}\b', ps_text))
        common_words = repo_words.intersection(ps_words)
        jaccard = len(common_words) / max(1, len(repo_words.union(ps_words)))

        # Direct cluster alignment
        if top_repo_cluster and top_ps_cluster and top_repo_cluster == top_ps_cluster:
            matched_label = domain_clusters[top_repo_cluster]["label"]
            score = round(78.0 + min(20.0, jaccard * 150 + (ps_cluster_scores[top_ps_cluster] * 2)), 1)
            return {
                "solves_same_core_problem": True,
                "aim_alignment_score": score,
                "domain_match": True,
                "reasoning": f"Strong intent alignment: Both the codebase and the problem statement focus directly on '{matched_label}' ({score:.1f}% intent score)."
            }

        # Check theme compatibility
        theme_matched = any(d in ps_theme_lower or ps_theme_lower in d for d in target_domains)
        if theme_matched:
            score = round(70.0 + min(25.0, jaccard * 180 + len(common_words)), 1)
            return {
                "solves_same_core_problem": True,
                "aim_alignment_score": score,
                "domain_match": True,
                "reasoning": f"Domain theme '{ps_theme}' aligns with project target domains ({score:.1f}% aim score, {len(common_words)} shared domain terms)."
            }

        # Hard Incompatibility Veto for disjoint clusters
        if top_repo_cluster and top_ps_cluster and top_repo_cluster != top_ps_cluster:
            repo_score = repo_cluster_scores.get(top_repo_cluster, 0)
            ps_score = ps_cluster_scores.get(top_ps_cluster, 0)
            if repo_score >= 2 and ps_score >= 2:
                repo_label = domain_clusters[top_repo_cluster]["label"]
                ps_label = domain_clusters[top_ps_cluster]["label"]
                veto_score = round(max(10.0, min(30.0, jaccard * 100)), 1)
                return {
                    "solves_same_core_problem": False,
                    "aim_alignment_score": veto_score,
                    "domain_match": False,
                    "reasoning": f"Intent mismatch: The repository is dedicated to '{repo_label}', whereas the SIH problem statement requires solutions for '{ps_label}' ({veto_score:.1f}% aim score)."
                }

        # Continuous generic compatibility score
        generic_score = round(40.0 + min(35.0, jaccard * 200 + len(common_words) * 2), 1)
        return {
            "solves_same_core_problem": True,
            "aim_alignment_score": generic_score,
            "domain_match": True,
            "reasoning": f"Cross-domain functional compatibility observed with '{ps_theme}' ({generic_score:.1f}% aim alignment)."
        }

    def _groq_full_corpus_triage(
        self,
        db: Session,
        repo_profile: Dict[str, Any],
        manifest: Dict[str, Any]
    ) -> List[str]:
        """
        Executes parallel full-corpus triage across all problem statements in batches of 15-20.
        Uses Groq LLM (or Heuristic provider if offline) to shortlist problem statement IDs
        that are plausibly related in real-world purpose to the project's Capability Manifest.
        """
        try:
            all_ps = db.query(
                ProblemStatement.id,
                ProblemStatement.title,
                ProblemStatement.theme,
                ProblemStatement.expected_solution,
                ProblemStatement.description
            ).all()
        except Exception as e:
            logger.warning(f"Failed to query full problem statement corpus for triage: {e}")
            return []

        if not all_ps:
            return []

        # If provider is purely heuristic, use domain signal filtering directly
        if not self.ai_provider or isinstance(self.ai_provider, HeuristicAIProvider):
            target_domains = [d.lower() for d in repo_profile.get("target_domains", [])]
            domain_signals = [s.lower() for s in (manifest.get("domain_signals") or repo_profile.get("domain_signals") or [])]
            
            shortlisted = []
            for ps in all_ps:
                t_lower = (ps.theme or "").lower()
                title_lower = (ps.title or "").lower()
                desc_lower = (ps.description or "").lower()
                sol_lower = (ps.expected_solution or "").lower()
                all_text = f"{t_lower} {title_lower} {desc_lower} {sol_lower}"
                
                # Check domain match
                if any(d in t_lower or t_lower in d for d in target_domains if d):
                    shortlisted.append(ps.id)
                elif any(s in all_text for s in domain_signals if s):
                    shortlisted.append(ps.id)
            return shortlisted

        # Build compact items for batching
        items = []
        for ps in all_ps:
            summary = (ps.expected_solution or ps.description or "")[:120].strip().replace("\n", " ")
            items.append({
                "id": ps.id,
                "title": ps.title[:90] if ps.title else "",
                "theme": ps.theme or "",
                "summary": summary
            })

        batch_size = 18
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        repo_summary = repo_profile.get("project_summary") or repo_profile.get("description") or "Software Project"
        repo_caps = ", ".join([c["name"] for c in manifest.get("capabilities", [])[:4]]) or "Application capabilities"
        repo_domains = ", ".join(repo_profile.get("target_domains", []))

        system_prompt = (
            "You are an expert AI triage architect for Smart India Hackathon. "
            "Your task is to select problem statement IDs that plausibly share the real-world domain, "
            "purpose, or problem-scope with the repository. Be broad and inclusive during triage; "
            "do not discard possible domain matches. Return only valid JSON with 'shortlisted_ids'."
        )

        def process_batch(batch_items: List[Dict[str, Any]]) -> List[str]:
            prompt = f"""REPOSITORY CONTEXT:
- Name: {repo_profile.get('repo_name', 'Repo')}
- Stated Purpose: {repo_summary}
- Target Domains: {repo_domains}
- Verified Capabilities: {repo_caps}

CANDIDATE PROBLEM STATEMENTS TO TRIAGE:
{json.dumps(batch_items, indent=2)}

TASK:
Review the candidates above. Return all candidate IDs that plausibly match or could be solved by transforming this project.
Respond ONLY with a valid JSON object:
{{
  "shortlisted_ids": ["ID1", "ID2"]
}}"""
            try:
                res = self.ai_provider.generate_json(prompt, system_prompt=system_prompt)
                if isinstance(res, dict) and "shortlisted_ids" in res:
                    valid_ids = {b["id"] for b in batch_items}
                    return [str(x) for x in res["shortlisted_ids"] if str(x) in valid_ids]
            except Exception as e:
                logger.warning(f"Groq triage batch failed: {e}")
            return []

        shortlisted_ids = set()
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_batch = {executor.submit(process_batch, b): b for b in batches}
            for future in as_completed(future_to_batch):
                try:
                    b_ids = future.result()
                    shortlisted_ids.update(b_ids)
                except Exception as e:
                    logger.warning(f"Error gathering triage batch results: {e}")

        logger.info(f"Full-corpus Groq triage shortlisted {len(shortlisted_ids)} candidates from {len(all_ps)} total problem statements.")
        return list(shortlisted_ids)

    def _retrieve_candidates(
        self,
        db: Session,
        repo_vec: List[float],
        analysis_data: Dict[str, Any],
        repo_profile: Dict[str, Any],
        manifest: Dict[str, Any]
    ) -> List[ProblemStatement]:
        """
        Retrieves candidate problem statements using an additive union of:
        1. Full-corpus parallel Groq triage pass (high recall across all ~226 PS).
        2. pgvector cosine distance top-25 search (semantic embedding retrieval).
        Logs candidate set sizes and overlap telemetry for observability.
        """
        # 1. Full-Corpus Groq Triage Pass
        groq_candidate_ids = set(self._groq_full_corpus_triage(db, repo_profile, manifest))

        # 2. Vector Cosine Search (pgvector)
        vec_candidate_ids = set()
        try:
            vec_str = "[" + ",".join(f"{x:.6f}" for x in repo_vec) + "]"
            sql = text("SELECT id FROM problem_statements ORDER BY embedding <=> (:vec)::vector LIMIT 25;")
            result = db.execute(sql, {"vec": vec_str}).fetchall()
            vec_candidate_ids = {r[0] for r in result}
        except Exception as e:
            logger.warning(f"Vector search failed: {e}. Falling back to domain query.")

        # Also include domain themes as safety supplement
        domains = analysis_data.get("target_domains", [])
        if domains:
            try:
                domain_conds = " OR ".join([f"theme ILIKE :d{i}" for i in range(len(domains))])
                params = {f"d{i}": f"%{d.split('/')[0].strip()}%" for i, d in enumerate(domains)}
                domain_sql = text(f"SELECT id FROM problem_statements WHERE {domain_conds} LIMIT 15;")
                d_result = db.execute(domain_sql, params).fetchall()
                for r in d_result:
                    vec_candidate_ids.add(r[0])
            except Exception as e:
                logger.warning(f"Domain search failed: {e}")

        # 3. Additive Union of Groq Triage and Vector Search
        union_ids = groq_candidate_ids.union(vec_candidate_ids)
        overlap_ids = groq_candidate_ids.intersection(vec_candidate_ids)

        logger.info(
            f"[Candidate Retrieval Telemetry] Total Union: {len(union_ids)} candidates | "
            f"Groq Triage: {len(groq_candidate_ids)} | Vector Search: {len(vec_candidate_ids)} | "
            f"Overlap: {len(overlap_ids)} candidates."
        )

        if union_ids:
            return db.query(ProblemStatement).filter(ProblemStatement.id.in_(list(union_ids))).all()

        return db.query(ProblemStatement).limit(35).all()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        db: Session = context["db"]
        analysis_data = context.get("analysis_data", {})
        repo_info = context.get("repo_info", {})
        manifest = analysis_data.get("capability_manifest") or {}
        
        # Build unified project semantic search string directly from Capability Manifest
        manifest_caps = manifest.get("capabilities", [])
        manifest_endpoints = manifest.get("endpoints", [])
        manifest_models = manifest.get("data_models", [])
        domain_signals = manifest.get("domain_signals") or analysis_data.get("domain_signals") or []

        cap_lines = [f"- {c.get('name')}: {'; '.join(c.get('evidence', []))}" for c in manifest_caps]
        ep_lines = [f"{ep.get('method')} {ep.get('path')}" for ep in manifest_endpoints[:8]]
        model_lines = [f"{m.get('model_name')} ({', '.join(m.get('columns', [])[:4])})" for m in manifest_models[:6]]

        project_rep = (
            f"Repository: {repo_info.get('repo_name', '')}\n"
            f"Purpose: {analysis_data.get('project_summary', repo_info.get('description', ''))}\n"
            f"Type: {analysis_data.get('project_type', '')}\n"
            f"Domain Signals: {', '.join(domain_signals)}\n"
            f"Languages & Tech: {', '.join(analysis_data.get('detected_languages', []))} | {', '.join(manifest.get('tech_stack', []))}\n"
            f"Code Capabilities:\n{chr(10).join(cap_lines) if cap_lines else 'Standard application services'}\n"
            f"API Endpoints: {', '.join(ep_lines) if ep_lines else 'None'}\n"
            f"Data Models: {', '.join(model_lines) if model_lines else 'None'}"
        )

        repo_profile = {
            "repo_name": repo_info.get("repo_name", ""),
            "description": repo_info.get("description", ""),
            "project_summary": analysis_data.get("project_summary", repo_info.get("description", "")),
            "core_features": analysis_data.get("core_features", []),
            "detected_features": analysis_data.get("core_features", []),
            "target_domains": analysis_data.get("target_domains", []),
            "domain_signals": domain_signals,
            "technical_capabilities": analysis_data.get("technical_capabilities", []),
            "detected_languages": analysis_data.get("detected_languages", []),
            "project_type": analysis_data.get("project_type", ""),
            "capability_manifest": manifest
        }

        # Generate vector embedding
        repo_vec = self.embedder.get_embedding(project_rep)
        embedding_fallback_active = self.embedder.is_fallback_active

        # Retrieve candidate problem statements from PostgreSQL via full-corpus Groq triage + vector union
        candidates = self._retrieve_candidates(db, repo_vec, analysis_data, repo_profile, manifest)

        scored_matches = []
        vetoed_matches = []

        for ps in candidates:
            # 1. Intent Alignment Step (Veto Guard)
            intent_result = self.assess_intent_alignment(repo_profile, ps)
            domain_match = intent_result.get("domain_match", False)
            aim_score = float(intent_result.get("aim_alignment_score", 0.0))

            if not domain_match or aim_score < 40.0:
                vetoed_matches.append({
                    "problem_statement_id": ps.id,
                    "title": ps.title,
                    "aim_alignment_score": aim_score,
                    "reasoning": intent_result.get("reasoning", "Vetoed due to domain intent mismatch.")
                })
                continue

            # 2. 6-Factor Multi-Dimensional Alignment Scoring against Capability Manifest
            score_data = self._score_match(ps, analysis_data, repo_vec, intent_result, manifest, repo_info)
            scored_matches.append(score_data)

        # Sort by overall match score descending
        scored_matches.sort(key=lambda x: x["overall_match_score"], reverse=True)
        
        # Ensure we provide top 3 matches (up to 6)
        top_matches = scored_matches[:max(3, min(6, len(scored_matches)))]

        # -------------------------------------------------------------
        # GUARDRAIL: Domain Mismatch Warning
        # If top match has tech_score < 55% and reusability < 30% while intent_score > 75%,
        # set domain_mismatch_warning: true and include next-best candidates.
        # -------------------------------------------------------------
        domain_mismatch_warning = False
        alternative_candidates = []

        if top_matches:
            top_m = top_matches[0]
            top_tech = top_m.get("tech_capability_score", 80.0)
            top_aim = top_m.get("aim_alignment_score", 0.0)
            top_feature = top_m.get("feature_alignment", 50.0)
            
            if top_tech < 55.0 and top_feature < 30.0 and top_aim > 75.0:
                domain_mismatch_warning = True
                top_m["domain_mismatch_warning"] = True
                alternative_candidates = scored_matches[1:4]
            else:
                top_m["domain_mismatch_warning"] = False

        top_str = ", ".join(f"{m['problem_statement_id']} ({m.get('overall_match_score', 0)}%)" for m in top_matches[:3])
        summary = f"Evaluated {len(candidates)} candidates ({len(vetoed_matches)} vetoed by Intent Guard). "
        if top_matches:
            summary += f"Top 3 matches: {top_str}"
        else:
            summary += "No candidates met the minimum intent threshold."

        return {
            "project_representation": project_rep,
            "repo_embedding": repo_vec,
            "embedding_fallback_active": embedding_fallback_active,
            "top_matches": top_matches,
            "vetoed_matches": vetoed_matches,
            "domain_mismatch_warning": domain_mismatch_warning,
            "alternative_candidates": alternative_candidates,
            "summary_output": summary
        }

    def _score_match(
        self,
        ps: ProblemStatement,
        analysis_data: Dict[str, Any],
        repo_vec: List[float],
        intent_result: Dict[str, Any],
        manifest: Dict[str, Any],
        repo_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculates 6-factor alignment score against the Capability Manifest with dynamic continuous overlap metrics."""
        # 1. Aim/Intent Alignment (30%)
        aim_score = round(float(intent_result.get("aim_alignment_score", 0.0)), 1)
        if aim_score <= 0.0:
            logger.warning(f"Zero aim_score computed for repo '{(repo_info or {}).get('repo_name')}' vs PS '{ps.id}'. Intent result: {intent_result}")

        # 2. Semantic Similarity (20%)
        ps_vec = ps.embedding
        if ps_vec is not None:
            raw_sim = self.embedder.cosine_similarity(repo_vec, list(ps_vec))
            semantic_score = round(raw_sim * 100, 1)
        else:
            logger.warning(f"Missing vector embedding for PS '{ps.id}'. Computing term overlap semantic score.")
            ps_text = (ps.title + " " + ps.description).lower()
            manifest_caps = [c["name"].lower() for c in manifest.get("capabilities", [])]
            hits = sum(1 for c in manifest_caps if any(w in ps_text for w in c.split()))
            semantic_score = round(min(90.0, max(20.0, 30.0 + hits * 15.0)), 1)

        # 3. Feature / Capability Alignment (20%)
        manifest_caps = [c["name"].lower() for c in manifest.get("capabilities", [])]
        features = [f.lower() for f in analysis_data.get("core_features", [])]
        all_feature_terms = list(set(manifest_caps + features))
        
        ps_text = (ps.title + " " + ps.description + " " + (ps.expected_solution or "")).lower()
        
        feature_hits = sum(1 for f in all_feature_terms if any(w in ps_text for w in f.split() if len(w) > 3))
        feature_score = min(100.0, round((feature_hits / max(1, len(all_feature_terms))) * 100, 1)) if all_feature_terms else 30.0

        # 4. Domain Alignment (10%) continuous calculation
        domain_signals = [s.lower() for s in (manifest.get("domain_signals") or analysis_data.get("domain_signals") or [])]
        target_domains = [d.lower() for d in analysis_data.get("target_domains", [])]
        ps_theme_lower = ps.theme.lower()
        ps_org_lower = ps.organization.lower()
        
        domain_signal_theme_map = {
            "education": ["smart education", "education", "skill", "learning", "pedagogy", "tutoring", "student"],
            "forecasting": ["transportation & logistics", "logistics", "supply chain", "demand", "smart automation", "agriculture"],
            "routing": ["transportation & logistics", "logistics", "travel", "fleet", "smart automation"],
            "scraping": ["smart automation", "software", "miscellaneous"],
            "webhook": ["smart automation", "software", "miscellaneous"],
            "geospatial": ["disaster management", "gis", "agriculture", "environment"],
            "cybersecurity": ["blockchain & cybersecurity", "cyber", "security", "defense"],
            "healthcare": ["medtech / biotech / healthtech", "healthcare", "medical", "hospital"]
        }

        # Calculate continuous signal hit ratio
        matching_signal_count = 0
        for sig in domain_signals:
            themes = domain_signal_theme_map.get(sig, [sig])
            if any(t in ps_theme_lower or t in ps_org_lower or t in ps_text for t in themes):
                matching_signal_count += 1

        if matching_signal_count > 0:
            domain_score = round(min(98.0, 65.0 + (matching_signal_count * 12.0)), 1)
        elif any(d in ps_theme_lower or ps_theme_lower in d for d in target_domains):
            domain_score = 75.0
        elif ps_theme_lower in ("miscellaneous", "smart automation"):
            domain_score = 55.0
        else:
            domain_score = 25.0

        # 5. Tech Capability Alignment (10%)
        tech_score = 80.0
        if ps.category.lower() == "hardware":
            if "Hardware / IoT / Embedded System" in analysis_data.get("project_type", ""):
                tech_score = 90.0
            else:
                tech_score = 35.0

        # 6. Expected Solution Alignment (10%)
        sol_score = round((semantic_score * 0.5 + feature_score * 0.5), 1)

        # Composite Score Calculation
        overall = round(
            (aim_score * 0.30) +
            (semantic_score * 0.20) +
            (feature_score * 0.20) +
            (domain_score * 0.10) +
            (tech_score * 0.10) +
            (sol_score * 0.10),
            1
        )

        # Apply low domain overlap penalty if domain_score is very low (< 35)
        if domain_score < 35.0:
            overall = round(overall * 0.82, 1)

        overall = max(10.0, min(98.5, overall))
        confidence = "High" if overall >= 80 else ("Medium" if overall >= 60 else "Low")

        # Grounded Existing vs Missing Capabilities
        existing = []
        for cap in manifest.get("capabilities", [])[:3]:
            existing.append(f"{cap['name']} ({'; '.join(cap.get('evidence', [])[:1])})")

        missing = []
        if "Geospatial Mapping & GIS" not in [c["name"] for c in manifest.get("capabilities", [])] and "gis" in ps_text:
            missing.append("Geospatial / mapping integration (GeoPandas, Leaflet)")
        if "REST API Service Layer" not in [c["name"] for c in manifest.get("capabilities", [])]:
            missing.append("Standardized REST API backend service")
        if ps.category.lower() == "hardware":
            missing.append("Embedded firmware / microcontroller interfacing")
        missing.append(f"Domain business logic for {ps.organization} ({ps.theme})")

        reasoning = intent_result.get("reasoning") or (
            f"The repository's purpose aligns with '{ps.title}' under {ps.theme}. "
            f"Code capabilities ({', '.join([c['name'] for c in manifest.get('capabilities', [])[:2]]) or 'services'}) "
            f"can be repurposed for {ps.organization}'s requirements."
        )

        return {
            "problem_statement_id": ps.id,
            "title": ps.title,
            "category": ps.category,
            "theme": ps.theme,
            "organization": ps.organization,
            "overall_match_score": overall,
            "aim_alignment_score": aim_score,
            "semantic_similarity": semantic_score,
            "feature_alignment": feature_score,
            "domain_alignment": domain_score,
            "tech_capability_score": tech_score,
            "solution_alignment_score": sol_score,
            "confidence": confidence,
            "match_reasoning": reasoning,
            "existing_capabilities": existing[:3],
            "missing_capabilities": missing[:3],
            "reusable_components": [c["name"] for c in manifest.get("capabilities", [])[:3]] or ["Data processing workflows"],
            "domain_mismatch_warning": False
        }
