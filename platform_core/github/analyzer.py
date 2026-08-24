"""
Static AST & Dependency Analyzer for GitHub Repositories.
Extracts architecture, frameworks, per-file AST findings (functions, classes, docstrings,
routes, ORM models, imports), and capability evidence without code execution.
"""

import ast
import re
from typing import Dict, Any, List, Set, Optional


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

        # -------------------------------------------------------------
        # PER-FILE STATIC CODE EXTRACTION (AST for Python, Regex for JS/TS)
        # -------------------------------------------------------------
        file_findings: List[Dict[str, Any]] = []
        aggregated_endpoints: List[Dict[str, Any]] = []
        aggregated_models: List[Dict[str, Any]] = []
        code_capabilities: List[Dict[str, Any]] = []
        domain_signals: Set[str] = set()

        for path, content in file_contents.items():
            ext = "." + path.split(".")[-1].lower() if "." in path else ""
            if ext == ".py":
                finding = cls._extract_python_ast(path, content)
                file_findings.append(finding)
                aggregated_endpoints.extend(finding.get("routes", []))
                aggregated_models.extend(finding.get("models", []))
                for cap in finding.get("inferred_capabilities", []):
                    code_capabilities.append(cap)
                for sig in finding.get("domain_signals", []):
                    domain_signals.add(sig)
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                finding = cls._extract_jsts_code(path, content)
                file_findings.append(finding)
                aggregated_endpoints.extend(finding.get("routes", []))
                aggregated_models.extend(finding.get("models", []))
                for cap in finding.get("inferred_capabilities", []):
                    code_capabilities.append(cap)
                for sig in finding.get("domain_signals", []):
                    domain_signals.add(sig)

        # Build formatted list of API routes
        api_routes = [f"{r['method']} {r['path']}" for r in aggregated_endpoints]

        # Detect Project Type
        project_type = "Software Application"
        if "Geospatial / GIS" in ml_caps or "geospatial" in domain_signals:
            project_type = "AI & Geospatial Intelligence System"
        elif "OpenCV / Computer Vision" in ml_caps or "computer_vision" in domain_signals:
            project_type = "Computer Vision & Edge AI System"
        elif "Supply Chain & Logistics" in detected_frameworks or "Time Series & Forecasting" in ml_caps or "forecasting" in domain_signals or "routing" in domain_signals:
            project_type = "Supply Chain & Predictive Analytics Platform"
        elif "Cybersecurity" in detected_frameworks or "cybersecurity" in domain_signals:
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

        # Detect Core Features with grounding
        readme_content = next((c for p, c in file_contents.items() if "readme" in p.lower()), "")
        detected_features = cls._extract_features(readme_content, repo_info, detected_frameworks, api_routes, code_capabilities)

        return {
            "project_type": project_type,
            "languages": sorted(list(langs)),
            "detected_frameworks": detected_frameworks,
            "frontend_framework": frontend,
            "backend_framework": backend,
            "database_tech": database,
            "ml_capabilities": ml_caps,
            "api_routes": api_routes[:20],
            "endpoints": aggregated_endpoints,
            "data_models": aggregated_models,
            "file_findings": file_findings,
            "code_capabilities": code_capabilities,
            "domain_signals": sorted(list(domain_signals)),
            "detected_features": detected_features,
            "readme_summary": readme_content[:1500] if readme_content else repo_info.get("description", "")
        }

    # -----------------------------------------------------------------
    # PYTHON AST STATIC PARSER
    # -----------------------------------------------------------------
    @classmethod
    def _extract_python_ast(cls, path: str, content: str) -> Dict[str, Any]:
        """Statically analyzes Python source using standard ast module without executing code."""
        finding: Dict[str, Any] = {
            "path": path,
            "language": "Python",
            "classes": [],
            "functions": [],
            "routes": [],
            "models": [],
            "imports": [],
            "inferred_capabilities": [],
            "domain_signals": []
        }

        try:
            tree = ast.parse(content)
        except Exception:
            # Fallback regex extraction if ast fails on syntax error
            finding["routes"] = cls._extract_routes_regex(path, content)
            return finding

        imported_modules: Set[str] = set()
        classes_info: List[Dict[str, Any]] = []
        functions_info: List[Dict[str, Any]] = []
        routes_info: List[Dict[str, Any]] = []
        models_info: List[Dict[str, Any]] = []

        # 1. Imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    imported_modules.add(root_mod)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split(".")[0]
                    imported_modules.add(root_mod)

        finding["imports"] = sorted(list(imported_modules))

        # 2. Class Definitions & ORM Models
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                
                # Check for SQLAlchemy / ORM / Pydantic models
                base_names = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        base_names.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        base_names.append(b.attr)

                is_orm_model = any(b in ("Base", "Model", "DeclarativeBase", "db.Model", "BaseModel") for b in base_names)
                
                # Look for __tablename__ and Column / Field assignments
                table_name = None
                columns: List[str] = []
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if target.id == "__tablename__" and isinstance(item.value, (ast.Constant, ast.Str)):
                                    table_name = getattr(item.value, "value", getattr(item.value, "s", None))
                                    is_orm_model = True
                                elif cls._is_column_assign(item.value):
                                    columns.append(target.id)
                                    is_orm_model = True
                    elif isinstance(item, ast.AnnAssign):
                        if isinstance(item.target, ast.Name):
                            columns.append(item.target.id)

                class_data = {
                    "name": node.name,
                    "docstring": docstring[:250],
                    "methods": methods,
                    "bases": base_names
                }
                classes_info.append(class_data)

                if is_orm_model or table_name or columns:
                    models_info.append({
                        "model_name": node.name,
                        "table_name": table_name or node.name.lower() + "s",
                        "columns": columns[:15],
                        "docstring": docstring[:200],
                        "file": path
                    })

            # 3. Functions & Route Decorators
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node) or ""
                is_async = isinstance(node, ast.AsyncFunctionDef)
                
                func_data = {
                    "name": node.name,
                    "docstring": docstring[:250],
                    "is_async": is_async
                }
                functions_info.append(func_data)

                # Route decorator detection: @app.get("/..."), @router.post("/..."), @bp.route(...)
                for dec in node.decorator_list:
                    route = cls._parse_route_decorator(dec, node.name, docstring, path)
                    if route:
                        routes_info.append(route)

        finding["classes"] = classes_info
        finding["functions"] = functions_info
        finding["routes"] = routes_info
        finding["models"] = models_info

        # 4. Synthesize Domain Signals and Named Capabilities from AST
        inferred_caps, domain_sigs = cls._infer_capabilities_from_ast(path, classes_info, functions_info, routes_info, models_info, imported_modules)
        finding["inferred_capabilities"] = inferred_caps
        finding["domain_signals"] = domain_sigs

        return finding

    @staticmethod
    def _is_column_assign(val_node: ast.AST) -> bool:
        """Helper to identify if an assignment is a database column or Pydantic Field."""
        if isinstance(val_node, ast.Call):
            if isinstance(val_node.func, ast.Name):
                return val_node.func.id in ("Column", "Field", "mapped_column", "relationship")
            elif isinstance(val_node.func, ast.Attribute):
                return val_node.func.attr in ("Column", "Field", "mapped_column", "relationship")
        return False

    @staticmethod
    def _parse_route_decorator(dec_node: ast.AST, handler_name: str, docstring: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Parses route decorator AST nodes into structured API route endpoints."""
        if not isinstance(dec_node, ast.Call):
            return None
        
        func = dec_node.func
        method = "GET"
        path_str = "/"

        if isinstance(func, ast.Attribute):
            attr_name = func.attr.lower()
            if attr_name in ("get", "post", "put", "delete", "patch", "options", "head", "websocket"):
                method = attr_name.upper()
            elif attr_name == "route":
                # Check methods=["POST"] keyword
                for kw in dec_node.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                        methods_list = [getattr(elt, "value", getattr(elt, "s", "GET")) for elt in kw.value.elts if isinstance(elt, (ast.Constant, ast.Str))]
                        if methods_list:
                            method = str(methods_list[0]).upper()
            else:
                return None
        else:
            return None

        if dec_node.args:
            first_arg = dec_node.args[0]
            if isinstance(first_arg, (ast.Constant, ast.Str)):
                path_str = getattr(first_arg, "value", getattr(first_arg, "s", "/"))

        return {
            "method": method,
            "path": path_str,
            "handler": handler_name,
            "docstring": docstring[:150],
            "file": file_path
        }

    # -----------------------------------------------------------------
    # JAVASCRIPT / TYPESCRIPT STATIC PARSER
    # -----------------------------------------------------------------
    @classmethod
    def _extract_jsts_code(cls, path: str, content: str) -> Dict[str, Any]:
        """Extracts routes, classes, functions, and imports from JS/TS source via regex."""
        finding: Dict[str, Any] = {
            "path": path,
            "language": "TypeScript" if path.endswith((".ts", ".tsx")) else "JavaScript",
            "classes": [],
            "functions": [],
            "routes": [],
            "models": [],
            "imports": [],
            "inferred_capabilities": [],
            "domain_signals": []
        }

        # Imports
        imports = re.findall(r'(?:import\s+(?:.*?\s+from\s+)?[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))', content)
        imported_modules = set()
        for i1, i2 in imports:
            mod = (i1 or i2).split("/")[0]
            if not mod.startswith("."):
                imported_modules.add(mod)
        finding["imports"] = sorted(list(imported_modules))

        # Routes
        routes_matches = re.findall(r'(?:app|router)\.(get|post|put|delete|patch|use)\s*\(\s*[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
        routes = []
        for m, p in routes_matches:
            routes.append({
                "method": m.upper(),
                "path": p,
                "handler": "handler",
                "docstring": "",
                "file": path
            })
        finding["routes"] = routes

        # Classes
        classes = re.findall(r'class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?', content)
        finding["classes"] = [{"name": c[0], "methods": [], "docstring": ""} for c in classes]

        # Functions
        funcs = re.findall(r'(?:async\s+)?function\s+([A-Za-z0-9_]+)|const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(', content)
        finding["functions"] = [{"name": f[0] or f[1], "docstring": "", "is_async": True} for f in funcs if f[0] or f[1]]

        inferred_caps, domain_sigs = cls._infer_capabilities_from_ast(
            path, finding["classes"], finding["functions"], routes, [], imported_modules
        )
        finding["inferred_capabilities"] = inferred_caps
        finding["domain_signals"] = domain_sigs

        return finding

    @classmethod
    def _extract_routes_regex(cls, path: str, content: str) -> List[Dict[str, Any]]:
        """Fallback regex route extractor."""
        routes = []
        for m, p in re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content, re.IGNORECASE):
            routes.append({
                "method": m.upper(),
                "path": p,
                "handler": "endpoint",
                "docstring": "",
                "file": path
            })
        return routes

    # -----------------------------------------------------------------
    # CAPABILITY & DOMAIN SIGNAL INFERENCE
    # -----------------------------------------------------------------
    @classmethod
    def _infer_capabilities_from_ast(
        cls,
        path: str,
        classes: List[Dict[str, Any]],
        functions: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        imports: Set[str]
    ) -> tuple:
        """Maps per-file AST elements to named capabilities and domain signals with explicit evidence citations."""
        capabilities: List[Dict[str, Any]] = []
        domain_signals: Set[str] = set()

        path_lower = path.lower()
        all_identifiers = " ".join(
            [path] +
            [c.get("name", "") + " " + c.get("docstring", "") for c in classes] +
            [f.get("name", "") + " " + f.get("docstring", "") for f in functions] +
            [r.get("path", "") + " " + r.get("handler", "") for r in routes] +
            [m.get("model_name", "") + " " + " ".join(m.get("columns", [])) for m in models] +
            list(imports)
        ).lower()

        # Domain Patterns to Match
        capability_lexicon = [
            ("Time-Series Demand Forecasting", [r"forecast", r"prophet", r"arima", r"predict_demand", r"demand_forecast"], "forecasting", "Supply Chain & Analytics"),
            ("Vehicle Routing & Optimization", [r"routing", r"route_opt", r"dijkstra", r"dispatch", r"fleet", r"osrm"], "routing", "Transportation & Logistics"),
            ("Web Scraping & DOM Extraction", [r"scraper", r"beautifulsoup", r"bs4", r"crawl", r"scrape", r"html_parser"], "scraping", "Smart Automation"),
            ("Webhook Automation & Event Dispatch", [r"webhook", r"event_dispatch", r"hmac", r"listener", r"callback", r"subscription"], "webhook", "Smart Automation"),
            ("Geospatial Mapping & GIS", [r"geopandas", r"folium", r"shapely", r"coordinates", r"spatial", r"geojson"], "geospatial", "Disaster Management & GIS"),
            ("Computer Vision & Edge Detection", [r"opencv", r"cv2", r"yolo", r"ultralytics", r"image_proc"], "computer_vision", "AI & Computer Vision"),
            ("Cybersecurity & Network Auditing", [r"scapy", r"packet", r"firewall", r"siem", r"cis_benchmark", r"vulnerability"], "cybersecurity", "Blockchain & Cybersecurity"),
            ("Biomedical Signal Processing", [r"eeg", r"brainwave", r"neuro", r"biomedical", r"patient_vitals"], "healthcare", "Healthcare & Biomedical"),
            ("Relational Data Persistence", [r"sqlalchemy", r"declarative_base", r"models\.py", r"database\.py"], "database", "Data Engineering"),
            ("REST API Service Layer", [r"fastapi", r"router\.get", r"router\.post", r"app\.get", r"blueprint"], "api", "Backend Engineering"),
        ]

        for cap_name, patterns, signal_key, domain_cat in capability_lexicon:
            matched_evidence = []
            for pat in patterns:
                if re.search(pat, all_identifiers):
                    domain_signals.add(signal_key)
                    # Find specific evidence items
                    for c in classes:
                        if re.search(pat, c["name"].lower() + " " + c.get("docstring", "").lower()):
                            matched_evidence.append(f"{path}: class {c['name']}")
                    for f in functions:
                        if re.search(pat, f["name"].lower() + " " + f.get("docstring", "").lower()):
                            matched_evidence.append(f"{path}: function {f['name']}()")
                    for r in routes:
                        if re.search(pat, r["path"].lower() + " " + r.get("handler", "").lower()):
                            matched_evidence.append(f"{path}: {r['method']} {r['path']}")
                    for m in models:
                        if re.search(pat, m["model_name"].lower() + " " + " ".join(m.get("columns", [])).lower()):
                            matched_evidence.append(f"{path}: model {m['model_name']} ({', '.join(m['columns'][:3])})")
                    break

            if matched_evidence:
                capabilities.append({
                    "name": cap_name,
                    "category": domain_cat,
                    "evidence": list(set(matched_evidence))[:4],
                    "confidence": 0.95 if len(matched_evidence) > 1 else 0.85,
                    "file": path
                })

        return capabilities, list(domain_signals)

    @staticmethod
    def _extract_features(
        readme: str,
        repo_info: Dict[str, Any],
        frameworks: List[str],
        api_routes: List[str],
        code_capabilities: List[Dict[str, Any]]
    ) -> List[str]:
        """Extracts grounded features prioritizing confirmed code capabilities over raw text."""
        features = []
        
        # Priority 1: Grounded code capabilities extracted from AST
        for cap in code_capabilities:
            name = cap.get("name")
            if name and name not in features:
                features.append(name)

        # Priority 2: Extract verified bullets from README
        if readme:
            matches = re.findall(r'(?:^|\n)\s*[•\-\*]\s*([A-Za-z0-9][^\n]{10,120})', readme)
            for m in matches[:10]:
                cleaned = m.strip()
                if not any(k in cleaned.lower() for k in ["license", "install", "http", "npm", "pip", "test", "clone", "git "]):
                    if cleaned not in features:
                        features.append(cleaned)

        # Priority 3: Confirmed frameworks and routes
        if not features:
            if frameworks:
                for fw in frameworks[:4]:
                    features.append(f"{fw} integration")
            if api_routes:
                features.append(f"REST API with {len(api_routes)} endpoints")
            if repo_info.get("description"):
                features.append(repo_info["description"][:100])

        return features[:10]
