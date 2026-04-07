# CLEAR Automated Analysis

## Client-Facing Next Steps and Delivery Roadmap

### Current Baseline

The CLEAR pipeline is currently reproducible and stable in local environments. The next phase focuses on production readiness, multilingual generalization, and operationalization as internal services.

### Priority Roadmap (Technical + Operational)

| Stream | Component | Current Status | Potential Improvements / Actions | Priority | Deployment Status |
|---|---|---|---|---|---|
| AI Feature | Entry Extraction | Optimized architecture; reliable for English; limited benchmarking on broader multilingual/non-Latin corpora | Build AI-assisted gold dataset; run multilingual benchmark campaign; retrain/upgrade extraction models for non-Latin scripts | High | Requires packaging as internal microservice |
| AI Feature | Entry Classification | Optimized and currently functional on Latin languages (`en`, `fr`, `es`) with level-1 and level-2 tagging | Retrain on updated multilingual ground truth; extend to additional languages; improve quality metrics and evaluation protocol | High | Requires packaging as internal microservice |
| AI Feature | Local LLM-Based Processing | Local document QA/RAG pipeline exists (llama-cpp based) | Harden deployment profiles for Linux/macOS/Windows; simplify private on-prem setup; define support boundaries | Medium | Requires packaging as internal microservice |
| AI Feature | Document Extraction | Functional across languages and formats (PDF + image OCR); accuracy acceptable but runtime/cost high | Refactor extraction flow to avoid unnecessary OCR/segmentation passes; optimize for volume; expand native support to `pptx` and `docx` | High | Requires packaging as internal microservice |
| AI Feature | Geolocation Extraction | Available with shapefile linkage | Generalize adapters and database connectors; improve geospatial normalization and confidence scoring | Medium | Requires packaging as internal microservice |
| Analysis Feature | Core Analytical Outputs | End-to-end outputs generated (risks, needs, interventions, indicators) | Conduct analyst-in-the-loop validation sessions; tune risk cutoffs and scoring logic; improve explainability traceability | High | Requires internal service deployment (external sharing optional) |
| Analysis Feature | Detailed Numerical Extraction | Partially implemented (e.g., displaced, killed, injured) | Expand indicator catalog by sector and pillar; improve temporal/location normalization; add confidence metadata | High | Pending deployment design |
| Product/UI | Analysis Dashboard and User Experience | Interactive dashboard available; currently best suited to technical users familiar with analytical terminology | Improve UX clarity, labels, and navigation; generalize views for multiple contexts/countries; add guided explanations and simplified outputs so non-technical users can interpret results confidently | High | Requires internal web-app deployment and user testing |
| Analysis Feature | Forecasting and Scenarios | Not yet implemented | Design scenario templates; add assumptions engine; implement forecasting workflow and evaluation criteria | Medium | Not deployed |
| AI Feature | Processed-Data Chatbot | Advanced retrieval chatbot prototype exists | Test on real analyst workflows; enforce output schema/guardrails; add response validation layer | Medium | Requires internal service deployment (external sharing optional) |
| Data Connectors | Source Coverage | Current ingestion relies primarily on ReliefWeb | Integrate additional structured/unstructured sources (including social media where relevant); implement connector governance and quality checks | High | Not deployed |
| Platform | Pipeline Orchestration and Storage | Full pipeline currently runs locally | Implement orchestrated microservice architecture; add scheduling, job monitoring, and persistent classification DB for reprocessing | Critical | Not deployed |

### Additional Potential Workstreams

These items are derived from capabilities described in project documentation and should be considered for roadmap sequencing.

| Stream | Component | Current Status | Potential Improvements / Actions | Priority | Deployment Status |
|---|---|---|---|---|---|
| Data Quality | Ground Truth and Benchmarking Framework | Ad hoc validation in place | Define versioned benchmark datasets and multilingual QA protocol for extraction/classification/analysis | High | Not deployed |
| Productization | Dashboard Packaging and Distribution | Dashboard generated as static HTML + JS artifacts | Package dashboard build outputs for standardized release process and client delivery lifecycle | Medium | Partially deployed (manual) |
| Platform Reliability | Idempotent Re-run and Recovery | Pipeline supports resumable steps locally | Add production-grade retry policies, run-state tracking, and observability dashboards | High | Not deployed |
| Governance | Model and Prompt Versioning | Prompt/model usage exists in scripts | Add formal model registry, prompt versioning, and audit trail for reproducibility and compliance | High | Not deployed |
| Security | Access Control for Internal Services | No centralized production controls yet | Add authentication, role-based access controls, and secure secret management for services | High | Not deployed |
| Performance | Cost and Latency Optimization | Current runs are acceptable for low volume | Define SLA targets; optimize parallelization and thresholds for high-volume country monitoring | Medium | Not deployed |

### Recommended Delivery Sequence

1. **Stabilize production foundation:** orchestration, scheduling, persistent storage, and service deployment.
2. **Scale multilingual quality:** benchmark framework, multilingual retraining, and analyst validation loops.
3. **Optimize performance and coverage:** extraction/runtime optimization and broader connector integration.
4. **Extend advanced outputs:** forecasting/scenarios and chatbot hardening once core reliability is established.