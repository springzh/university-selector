#!/usr/bin/env python3
"""MCP Server for Gaokao admission database queries."""
import os
import sys
import gzip
import shutil
import sqlite3
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent

# ── Paths ────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(ROOT, "admission_clean.db")
GZ_PATH = os.path.join(ROOT, "admission_clean.db.gz")

# ── Database initialization ───────────────────────────
def ensure_db():
    """Auto-decompress .db.gz if .db doesn't exist. Open read-only connection."""
    if not os.path.exists(DB_PATH) and os.path.exists(GZ_PATH):
        with gzip.open(GZ_PATH, "rb") as gz:
            with open(DB_PATH, "wb") as f:
                shutil.copyfileobj(gz, f)

    # Open read-only using URI mode with immutable query parameter
    db_uri = f"file:{DB_PATH}?mode=ro&immutable=1"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn

conn = ensure_db()

# ── MCP Server ────────────────────────────────────────
server = Server("gaokao-admission")

@server.tool()
async def query_admission(
    province: str | None = None,
    school: str | None = None,
    major: str | None = None,
    max_rank: int | None = None,
    min_rank: int | None = None,
    year: int = 2024,
    limit: int = 20,
) -> str:
    """Query admission database with flexible parameter combinations.

    At least one of `province` or `school` must be provided. All text
    parameters use SQL LIKE fuzzy matching (substring match).

    Args:
        province: Province name for fuzzy matching (e.g. '湖北')
        school: School name keyword for fuzzy matching (e.g. '武汉理工')
        major: Major name keyword for fuzzy matching (e.g. '计算机')
        max_rank: Upper bound for admission rank (inclusive)
        min_rank: Lower bound for admission rank (inclusive)
        year: Admission year, default 2024
        limit: Max results to return, default 20, hard cap 50

    Returns:
        JSON array of matching records sorted by year DESC, rank ASC.
        Each record: {school, major, score, rank, province, year}
    """
    import json

    # Validate: at least province or school required
    if not province and not school:
        return json.dumps(
            {"error": "At least `province` or `school` must be provided"},
            ensure_ascii=False,
        )

    # Clamp limit
    limit = min(max(1, limit), 50)

    # Build query dynamically
    conditions = []
    params = []

    if province:
        conditions.append("province LIKE ?")
        params.append(f"%{province}%")

    if school:
        conditions.append("school LIKE ?")
        params.append(f"%{school}%")

    if major:
        conditions.append("major LIKE ?")
        params.append(f"%{major}%")

    if max_rank is not None:
        conditions.append("rank IS NOT NULL AND rank <= ?")
        params.append(max_rank)

    if min_rank is not None:
        conditions.append("rank IS NOT NULL AND rank >= ?")
        params.append(min_rank)

    where = " AND ".join(conditions)

    sql = (
        f"SELECT school, major, score, rank, province, year "
        f"FROM admission "
        f"WHERE {where} "
        f"ORDER BY year DESC, rank ASC "
        f"LIMIT ?"
    )
    params.append(limit)

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = [
            {
                "school": row["school"],
                "major": row["major"] if row["major"] else "",
                "score": row["score"],
                "rank": row["rank"],
                "province": row["province"],
                "year": row["year"],
            }
            for row in rows
        ]

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@server.tool()
async def list_provinces() -> str:
    """List available provinces with record counts and year ranges.

    Returns:
        JSON array sorted by record_count DESC.
        Each entry: {province, record_count, years}
    """
    import json

    cursor = conn.cursor()
    cursor.execute(
        "SELECT province, COUNT(*) AS cnt, "
        "MIN(year) AS min_year, MAX(year) AS max_year "
        "FROM admission "
        "GROUP BY province "
        "ORDER BY cnt DESC"
    )
    rows = cursor.fetchall()

    results = [
        {
            "province": row["province"],
            "record_count": row["cnt"],
            "years": f"{row['min_year']}-{row['max_year']}",
        }
        for row in rows
    ]

    return json.dumps(results, ensure_ascii=False, indent=2)


# ── Entry point ───────────────────────────────────────
if __name__ == "__main__":
    server.run(transport="stdio")
