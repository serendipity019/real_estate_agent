"""
scripts/ingest_sample_data.py — Bulk-ingest the sample knowledge base text files
into the running Smart Real Estate Assistant API.

Usage:
    1. Start the server from backend folder: uvicorn app.main:app --reload
    2. Get a superuser JWT token (login as FIRST_SUPERUSER)
    3. Run: python scripts/ingest_sample_data.py --token <your_jwt_token>

    Or, to log in automatically with credentials from .env:
    python scripts/ingest_sample_data.py --email admin@example.com --password yourpassword
"""

import argparse
import os
import sys
from pathlib import Path

import httpx

KB_DIR = Path(__file__).parent.parent / "data" / "sample_knowledge_base"
BASE_URL = os.environ.get("SRA_BASE_URL", "http://localhost:8000")

# filename -> category mapping (matches the category noted inside each .txt file)
CATEGORY_MAP = {
    "01_neighborhood_prices.txt": "market_data",
    "02_rental_prices.txt": "market_data",
    "03_bank_of_greece_index.txt": "market_data",
    "04_valuation_methodology.txt": "general",
    "05_legal_golden_visa.txt": "legal",
}


def get_token(email: str, password: str) -> str:
    resp = httpx.post(
        f"{BASE_URL}/login/access-token",
        data={"username": email, "password": password},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def ingest_file(token: str, filepath: Path, category: str) -> None:
    content = filepath.read_text(encoding="utf-8")
    resp = httpx.post(
        f"{BASE_URL}/knowledge/ingest",
        json={
            "content": content,
            "source": filepath.name,
            "category": category,
            "metadata": {"origin": "sample_knowledge_base"},
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"  ✅ {filepath.name} → {data['documents_added']} chunk(s) "
          f"(collection size now: {data['collection_size']})")


def main():
    parser = argparse.ArgumentParser(description="Ingest sample files into the SRA API.")
    parser.add_argument("--token", help="Existing superuser JWT token")
    parser.add_argument("--email", help="Superuser email (used if --token not given)")
    parser.add_argument("--password", help="Superuser password (used if --token not given)")
    args = parser.parse_args()

    if args.token:
        token = args.token
    elif args.email and args.password:
        print(f"Logging in as {args.email}...")
        token = get_token(args.email, args.password)
        print("✅ Login successful.\n")
    else:
        print("Error: provide either --token, or both --email and --password.", file=sys.stderr)
        sys.exit(1)

    if not KB_DIR.exists():
        print(f"Error: knowledge base directory not found at {KB_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Ingesting sample knowledge base from {KB_DIR}...\n")
    for filename, category in CATEGORY_MAP.items():
        filepath = KB_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  Skipping {filename} (not found)")
            continue
        ingest_file(token, filepath, category)

    print("\n✅ Done. Verify with: GET /knowledge/stats")


if __name__ == "__main__":
    main()
