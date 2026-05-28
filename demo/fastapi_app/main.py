"""devsecops-coral demo app for Sentry error seeding.

A FastAPI application with intentionally vulnerable code paths that generate
real errors for Sentry. Used for hackathon data seeding.

Usage::

    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

    curl http://localhost:8000/vulnerable
    curl http://localhost:8000/unhandled
    curl http://localhost:8000/dependency-error
"""

import os

import sentry_sdk
from fastapi import FastAPI, HTTPException
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

# Initialize Sentry — replace with your DSN
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        environment="hackathon-demo",
        release="devsecops-coral-demo@0.1.0",
    )

app = FastAPI(
    title="DevSecOps Demo App",
    description="Intentionally vulnerable app for Sentry data seeding",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Health check endpoint — no errors."""
    return {"status": "running", "app": "coral-signal-seed"}


@app.get("/vulnerable")
async def vulnerable_json_parse():
    """Simulates a JSONDecodeError from parsing untrusted input."""
    import json

    data = json.loads("{invalid json payload from external API")
    return data


@app.get("/unhandled")
async def unhandled_exception():
    """Simulates an unhandled ValueError in a dependency path."""
    raise ValueError(
        "Unexpected input format in dependency processing pipeline. "
        "Check if django package version handles this input correctly."
    )


@app.get("/dependency-error")
async def dependency_error():
    """Simulates an ImportError from a broken dependency after a patch."""
    try:
        from deprecated_module import vulnerable_function  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as e:
        raise ImportError(
            f"Critical dependency missing after security patch: {e}. "
            "This may indicate an incomplete CVE remediation."
        ) from e


@app.get("/timeout")
async def simulated_timeout():
    """Simulates a slow endpoint for Sentry performance monitoring."""
    import asyncio

    await asyncio.sleep(10)
    return {"status": "eventually completed"}


@app.get("/memory")
async def memory_pressure():
    """Simulates memory pressure from processing large payloads."""
    try:
        data = [0] * (10**7)
        return {"allocated_items": len(data)}
    except MemoryError:
        raise HTTPException(
            status_code=503,
            detail="Service under memory pressure — possible DoS vector",
        )


@app.get("/pillow-error")
async def pillow_image_error():
    """Simulate a pillow image-processing failure (seeds the ACTIVE exploitation scenario).

    Call this endpoint 12 times to trigger the ``error_count >= 10`` threshold
    that marks pillow as an ACTIVE exploitation signal in the correlation query.
    """
    try:
        # Simulate the kind of error pillow CVE GHSA-ppf2-m228 can trigger
        raise ValueError(
            "pillow: decompression bomb protection triggered — "
            "image exceeds MAX_IMAGE_PIXELS limit (CVE / GHSA-ppf2-m228). "
            "Upgrade pillow >= 10.3.0 to apply the security fix."
        )
    except ValueError as exc:
        if SENTRY_DSN:
            sentry_sdk.capture_exception(exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/generate-errors")
async def generate_batch_errors():
    """Generate a batch of diverse errors for Sentry seeding."""
    errors = []

    try:
        response = {"data": {"users": []}}
        _ = response["data"]["missing_key"]
    except KeyError as e:
        sentry_sdk.capture_exception(e)
        errors.append("KeyError captured")

    try:
        _ = "string" + 42  # noqa: B018
    except TypeError as e:
        sentry_sdk.capture_exception(e)
        errors.append("TypeError captured")

    try:
        _ = 100 / 0  # noqa: B018
    except ZeroDivisionError as e:
        sentry_sdk.capture_exception(e)
        errors.append("ZeroDivisionError captured")

    return {
        "status": "errors generated",
        "count": len(errors),
        "errors": errors,
        "note": "Check your Sentry dashboard for captured events",
    }
