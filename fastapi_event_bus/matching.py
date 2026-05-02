"""
Segment-based wildcard pattern matching for event names.

Rules:
- "*"  matches exactly one segment
- "**" matches one or more segments (greedy, must be last segment in pattern)
- Any other segment must match exactly (case-sensitive)

Examples:
    matches("user.*", "user.created")    → True
    matches("user.*", "user.role.changed") → False
    matches("user.**", "user.role.changed") → True
    matches("user.**", "user")           → False
    matches("**", "user")               → True
    matches("**", "a.b.c")             → True
"""


def matches(pattern: str, event: str) -> bool:
    """Return True if event matches pattern."""
    pattern_segs = pattern.split(".")
    event_segs = event.split(".")

    has_globstar = "**" in pattern_segs

    if not has_globstar:
        # Exact segment count required
        if len(pattern_segs) != len(event_segs):
            return False
        return all(_seg_matches(p, e) for p, e in zip(pattern_segs, event_segs))

    # "**" must be the last segment (enforced by design)
    globstar_idx = pattern_segs.index("**")
    prefix_segs = pattern_segs[:globstar_idx]

    # event must have at least (prefix length + 1) segments
    # e.g. "user.**" needs at least 2 segments: "user" + something
    if len(event_segs) < len(prefix_segs) + 1:
        return False

    # Match prefix segments one-by-one
    for p, e in zip(prefix_segs, event_segs):
        if not _seg_matches(p, e):
            return False

    # "**" consumes the rest — always matches at this point
    return True


def _seg_matches(pattern_seg: str, event_seg: str) -> bool:
    """Return True if a single pattern segment matches a single event segment."""
    if pattern_seg == "*":
        return True
    return pattern_seg == event_seg