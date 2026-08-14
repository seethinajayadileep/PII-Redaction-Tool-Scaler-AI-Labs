"""Production server for Railway and Docker."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # Bind IPv6 all-interfaces. Railway Metal healthchecks and edge
    # traffic use IPv6; uvicorn --host 0.0.0.0 is IPv4-only and fails
    # with "service unavailable".
    uvicorn.run(
        "app:app",
        host="::",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
