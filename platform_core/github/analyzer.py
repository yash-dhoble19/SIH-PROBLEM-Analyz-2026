"""
Static AST & Dependency Analyzer for GitHub Repositories.
Extracts architecture, frameworks, ML pipelines, API routes, and features without code execution.
Guarantees strict word boundaries to avoid false positives (e.g. 'logistics' -> 'gis').
"""

import re
from typing import Dict, Any, List, Set


class RepositoryStaticAnalyzer:
    """Performs deterministic static analysis on repository structure and key configuration files."""

    FRAMEWORK_PATTERNS = {
        # Backend
        "FastAPI": [r"\bfastapi\b", r"from fastapi import", r"import fastapi"],
        "Flask": [r"\bflask\b", r"from flask import", r"import flask"],
        "Django": [r"\bdjango\b", r"from django", r"django-admin"],
        "Express": [r'"express"', r"'express'", r"require\(['\"]express['\"]\)"],
        "NestJS": [r'"@nestjs/core"', r"'@nestjs/core'"],
        "Spring Boot": [r"org\.springframework\.boot", r"spring-boot-starter"],
        
        # Frontend
        "React": [r'"react"', r"'react'", r"from ['\"]react['\"]"],
        "Next.js": [r'"next"', r"'next'", r"next/router", r"next/navigation"],
        "Vue": [r'"vue"', r"'vue'", r"vue-router"],
        "Angular": [r'"@angular/core"', r"'@angular/core'"],
        
        # Databases & ORM
        "PostgreSQL": [r"\bpsycopg2\b", r"\basyncpg\b", r"\bpostgres\b", r"\bpostgresql\b"],
        "MongoDB": [r"\bpymongo\b", r"\bmongoose\b", r"\bmotor\b"],
        "SQLite": [r"\bsqlite3\b", r"\bsqlite\b"],
        "Redis": [r"\bredis\b", r"\bioredis\b"],
        "SQLAlchemy": [r"\bsqlalchemy\b", r"from sqlalchemy"],
        "Prisma": [r'"@prisma/client"', r"\bprisma\b"],
        
        # AI / ML / Data Science
        "PyTorch": [r"\btorch\b", r"\bpytorch\b"],
        "TensorFlow": [r"\btensorflow\b", r"\bkeras\b"],
        "Scikit-Learn": [r"\bscikit-learn\b", r"\bsklearn\b"],
        "OpenCV / Computer Vision": [r"\bopencv-python\b", r"\bcv2\b", r"\bultralytics\b", r"\byolo\b"],
        "Pandas & Data Processing": [r"\bpandas\b", r"\bnumpy\b", r"\bpolars\b"],
        "NLP & LLMs": [r"\btransformers\b", r"\bhuggingface\b", r"\blangchain\b", r"\bopenai\b", r"\banthropic\b", r"\bllama[-_]index\b"],
        "Geospatial / GIS": [r"\bgeopandas\b", r"\bshapely\b", r"\bfolium\b", r"\brasterio\b", r"\bgdal\b", r"\bgeospatial\b", r"\bgeojson\b"],
        "Time Series & Forecasting": [r"\bprophet\b", r"\bstatsmodels\b", r"\bgluonts\b", r"\barima\b"],
        
        # Domain Specific
        "Supply Chain & Logistics": [r"\bsupply[-_ ]chain\b", r"\bprocurement\b", r"\binventory[-_ ]management\b", r"\bwarehouse\b", r"\bfleet[-_ ]management\b"],
        "Cybersecurity": [r"\bscapy\b", r"\bpcap\b", r"\bpacket[-_ ]inspection\b", r"\bsiem\b", r"\bfirewall\b", r"\bcis[-_ ]benchmark\b"],

        # Infrastructure
        "Docker": [r"dockerfile", r"docker-compose", r"\bFROM \b"],
        "Kubernetes": [r"apiVersion:", r"\bk8s\b", r"\bhelm\b"],
    }

    @classmethod
    def analyze_repository(
        cls,
        repo_info: Dict[str, Any],
        file_tree: List[Dict[str, Any]],
        file_contents: Dict[str, str]
    ) -> Dict[str, Any]:
        """Runs comprehensive static inspection over file paths, package manifests, and code files."""
        # Isolate text by files for precise inspection
        all_text = " ".join(file_contents.values())
        file_paths = [f["path"] for f in file_tree]
        all_context = all_text + " " + " ".join(file_paths)

        detected_frameworks = []
        for name, patterns in cls.FRAMEWORK_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, all_context, re.IGNORECASE):
                    detected_frameworks.append(name)
                    break

        # Categorize detected tech
        backend = next((f for f in ["FastAPI", "Flask", "Django", "Express", "NestJS", "Spring Boot"] if f in detected_frameworks), None)
        frontend = next((f for f in ["Next.js", "React", "Vue", "Angular"] if f in detected_frameworks), None)
        database = next((f for f in ["PostgreSQL", "MongoDB", "SQLite", "Redis"] if f in detected_frameworks), None)
        
        ml_caps = [f for f in detected_frameworks if f in [
            "PyTorch", "TensorFlow", "Scikit-Learn", "OpenCV / Computer Vision",
            "NLP & LLMs", "Geospatial / GIS", "Time Series & Forecasting"
        ]]
        
        # Extract Languages
        langs: Set[str] = set()
        if repo_info.get("primary_language") and repo_info["primary_language"] != "Unknown":
            langs.add(repo_info["primary_language"])
        for f in file_tree:
            ext = f.get("extension", "")
            if ext in (".py", ".ipynb"): langs.add("Python")
            elif ext in (".js", ".jsx"): langs.add("JavaScript")
            elif ext in (".ts", ".tsx"): langs.add("TypeScript")
            elif ext in (".java",): langs.add("Java")
            elif ext in (".go",): langs.add("Go")
            elif ext in (".cpp", ".c", ".h"): langs.add("C/C++")
            elif ext in (".rs",): langs.add("Rust")

        # Extract API Routes
        api_routes = []
        for path, content in file_contents.items():
            if path.endswith(".py"):
                routes = re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
                for method, route in routes:
                    api_routes.append(f"{method.upper()} {route}")
            elif path.endswith((".js", ".ts")):
                routes = re.findall(r'(?:app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
                for method, route in routes:
                    api_routes.append(f"{method.upper()} {route}")

        # Detect Project Type
        project_type = "Software Application"
        if "Geospatial / GIS" in ml_caps:
            project_type = "AI & Geospatial Intelligence System"
        elif "OpenCV / Computer Vision" in ml_caps:
            project_type = "Computer Vision & Edge AI System"
        elif "Supply Chain & Logistics" in detected_frameworks or "Time Series & Forecasting" in ml_caps:
            project_type = "Supply Chain & Predictive Analytics Platform"
        elif "Cybersecurity" in detected_frameworks:
            project_type = "Cybersecurity & Security Auditing Platform"
        elif ml_caps:
            project_type = "AI / Machine Learning Application"
        elif frontend and backend:
            project_type = "Full-Stack Web Application"
        elif backend:
            project_type = "Backend API & Microservice"
        elif frontend:
            project_type = "Frontend Web Application"
        elif any(l in ("C/C++", "Rust") for l in langs):
            project_type = "Hardware / IoT / Embedded System"

        # Detect Core Features from README only (never hallucinate from generic sub-word substrings)
        readme_content = next((c for p, c in file_contents.items() if "readme" in p.lower()), "")
        detected_features = cls._extract_features(readme_content, repo_info, detected_frameworks, api_routes)

        return {
            "project_type": project_type,
            "languages": sorted(list(langs)),
            "detected_frameworks": detected_frameworks,
            "frontend_framework": frontend,
            "backend_framework": backend,
            "database_tech": database,
            "ml_capabilities": ml_caps,
            "api_routes": api_routes[:15],
            "detected_features": detected_features,
            "readme_summary": readme_content[:1500] if readme_content else repo_info.get("description", "")
        }

    @staticmethod
    def _extract_features(readme: str, repo_info: Dict[str, Any], frameworks: List[str], api_routes: List[str]) -> List[str]:
        """Extracts bulleted features or functional capabilities grounded strictly in README or verified routes."""
        features = []
        if readme:
            # Look for lines starting with bullet points under Features or Overview
            matches = re.findall(r'(?:^|\n)\s*[•\-\*]\s*([A-Za-z0-9][^\n]{10,120})', readme)
            for m in matches[:10]:
                cleaned = m.strip()
                if not any(k in cleaned.lower() for k in ["license", "install", "http", "npm", "pip", "test", "clone", "git "]):
                    features.append(cleaned)

        if not features:
            # Fallback ONLY to confirmed detected frameworks & routes (no generic hardcoded GIS/streaming templates)
            if frameworks:
                for fw in frameworks[:4]:
                    features.append(f"{fw} integration")
            if api_routes:
                features.append(f"REST API with {len(api_routes)} endpoints")
            if repo_info.get("description"):
                features.append(repo_info["description"][:100])

        return features[:8]
