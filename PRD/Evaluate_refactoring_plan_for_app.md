# Architecture Refactoring Roadmap: Property Data App

This document outlines the transition from a monolithic Flask/HTML setup to a scalable, decoupled architecture optimized for Australian property data.

## 1. High-Level Architecture
We are moving to a **Decoupled Architecture**:
* **Frontend:** Next.js (React) for high-performance UI and state management.
* **Backend:** FastAPI (Python) to handle heavy data processing and AI logic.
* **Database:** PostgreSQL with PostGIS for spatial queries.

## 2. Directory Structure Refactor
Proposed structure for better modularity:

```text
/root
├── /webapp             # Next.js Frontend
│   ├── /src/components # UI Components
│   ├── /src/hooks      # React Query hooks for data fetching
│   └── /src/api        # Service layer to call backend
├── /backend            # FastAPI Backend
│   ├── /api/routes     # Endpoints
│   ├── /services       # Heavy logic (property_service.py)
│   ├── /models         # Pydantic schemas
│   └── /database       # SQLAlchemy models
├── /database           # Migration scripts
└── /scripts            # Data ingestion/cleaning scripts

## 3. Implementation Priorities
** Phase 1: API Extraction (The "FastAPI" Layer)
[ ] Migrate current Flask routes to FastAPI.

[ ] Implement Pydantic models to validate property data.

[ ] Enable PostGIS for location-based search queries.

[ ] Refactor business logic into a services/ layer.

Phase 2: Frontend Modernization (The "Next.js" Layer)
[ ] Initialize Next.js project.

[ ] Implement TanStack Query to replace raw fetch calls.

[ ] Replace HTML templates with reusable React components.

[ ] Use Server-Side Rendering (SSR) for SEO-critical property pages.

Phase 3: Performance Tuning
[ ] Pagination: Implement cursor-based pagination for large datasets.

[ ] Caching: Integrate Redis for frequently accessed property queries.

[ ] Background Tasks: Use Celery to offload heavy reports (e.g., generating PDFs or market analysis).

4. Key Performance Benefits
Concurrency: FastAPI's async capabilities will keep the server responsive while processing data.

Maintainability: Separation of concerns allows for independent deployment and testing.

Spatial Efficiency: PostGIS ensures your Australian property radius searches are executed at the database level, not the application level.


Phase 0 (Stabilize)
  └─ Write integration tests for existing Flask endpoints
  └─ Add Pydantic input validation to existing blueprints

Phase 1 (Service Layer — still on Flask)
  └─ Move SQL + business logic out of blueprints into services/
  └─ Blueprints become thin: validate → call service → return JSON
  └─ Migrate auth to JWT (required for stateless Next.js consumption)

Phase 2 (FastAPI swap — backend only)
  └─ Port blueprints to FastAPI routes (1:1, no logic changes)
  └─ Services/ layer is untouched — this is the payoff of Phase 1
  └─ Run Flask and FastAPI in parallel behind a proxy if needed

Phase 3 (Next.js frontend)
  └─ Backend API is now stable, typed, and documented (FastAPI gives you /docs free)
  └─ Build Next.js against the FastAPI endpoints route by route
  └─ Use strangler-fig: serve new React pages alongside old templates during transition