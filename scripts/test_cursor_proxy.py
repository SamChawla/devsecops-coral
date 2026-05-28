"""Quick smoke test for Cursor proxy chat completions."""

import httpx


def main() -> None:
    """POST a sample chat completion to the local Cursor proxy and print the response."""
    response = httpx.post(
        "http://localhost:4646/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Return JSON only with keys sql and reasoning. "
                        "sql must be: SELECT id FROM osv.search_vulnerabilities"
                        "(package => 'django', ecosystem => 'PyPI') LIMIT 1"
                    ),
                }
            ],
            "max_tokens": 400,
            "temperature": 0.2,
        },
        timeout=120.0,
    )
    print("status:", response.status_code)
    print(response.text[:2000])


if __name__ == "__main__":
    main()
