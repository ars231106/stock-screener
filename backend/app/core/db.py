"""Typed accessors for Supabase responses.

supabase-py types `response.data` as a broad JSON union
(`bool | str | int | float | Sequence[JSON] | Mapping[str, JSON] | None`),
which is accurate for the wire format and useless at the call site: every
`.get()` on a row becomes a type error.

In practice a PostgREST select always returns a list of objects. These
helpers assert that once, here, so the rest of the codebase can be typed
honestly instead of carrying an ignore comment on every query.
"""

from __future__ import annotations

from typing import Any

Row = dict[str, Any]

# supabase-py types this parameter as a CountMethod enum it does not export
# usefully. Naming it once here keeps the cast out of every call site.
EXACT: Any = "exact"


def rows(response: Any) -> list[Row]:
    """Every row of a select, or an empty list."""
    data = getattr(response, "data", None)
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict)]


def first(response: Any) -> Row | None:
    """The first row, or None. For `.limit(1)` lookups."""
    found = rows(response)
    return found[0] if found else None


def count_of(response: Any) -> int:
    """The exact count from a `select(..., count="exact")` query."""
    value = getattr(response, "count", None)
    return value if isinstance(value, int) else 0
