"""
Glasswatch External API Simulators

Production-quality simulators for all external integrations.
Allows full integration testing without real credentials.

Usage:
    uvicorn backend.simulators.external_apis:app --port 8099

Set SIMULATOR_MODE=true in the environment to route integration calls
to the local simulator instead of real endpoints.
"""
