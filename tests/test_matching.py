"""
Tests for segment-based wildcard pattern matching.
"""
import pytest
from fastapi_event_bus.matching import matches


class TestExactMatch:
    def test_exact_match(self):
        assert matches("user.created", "user.created") is True

    def test_exact_no_match_different_event(self):
        assert matches("user.created", "user.deleted") is False

    def test_exact_no_match_extra_segment(self):
        assert matches("user.created", "user.created.extra") is False

    def test_exact_no_match_missing_segment(self):
        assert matches("user.created", "user") is False

    def test_exact_single_segment(self):
        assert matches("ping", "ping") is True

    def test_exact_single_segment_no_match(self):
        assert matches("ping", "pong") is False


class TestSingleWildcard:
    def test_star_matches_one_segment(self):
        assert matches("user.*", "user.created") is True

    def test_star_matches_different_second_segment(self):
        assert matches("user.*", "user.deleted") is True

    def test_star_does_not_match_two_segments(self):
        assert matches("user.*", "user.role.changed") is False

    def test_star_does_not_match_zero_extra_segments(self):
        assert matches("user.*", "user") is False

    def test_star_prefix_match(self):
        assert matches("*.created", "user.created") is True
        assert matches("*.created", "order.created") is True

    def test_star_prefix_no_match(self):
        assert matches("*.created", "user.deleted") is False

    def test_star_middle(self):
        assert matches("a.*.c", "a.b.c") is True
        assert matches("a.*.c", "a.x.c") is True
        assert matches("a.*.c", "a.b.d") is False

    def test_star_only(self):
        assert matches("*", "anything") is True
        assert matches("*", "two.segments") is False


class TestDoubleWildcard:
    def test_globstar_matches_one_extra_segment(self):
        assert matches("user.**", "user.created") is True

    def test_globstar_matches_two_extra_segments(self):
        assert matches("user.**", "user.role.changed") is True

    def test_globstar_matches_three_extra_segments(self):
        assert matches("user.**", "user.a.b.c") is True

    def test_globstar_does_not_match_base_only(self):
        # "user.**" requires at least one segment after "user"
        assert matches("user.**", "user") is False

    def test_globstar_does_not_match_different_prefix(self):
        assert matches("user.**", "order.created") is False

    def test_globstar_alone_matches_single_segment(self):
        assert matches("**", "user") is True

    def test_globstar_alone_matches_multi_segment(self):
        assert matches("**", "user.created") is True
        assert matches("**", "a.b.c.d") is True

    def test_globstar_prefix_two_segments(self):
        assert matches("order.item.**", "order.item.added") is True
        assert matches("order.item.**", "order.item.removed") is True
        assert matches("order.item.**", "order.item.tag.added") is True
        assert matches("order.item.**", "order.item") is False
        assert matches("order.item.**", "order.created") is False


class TestEdgeCases:
    def test_empty_pattern_and_event(self):
        # Both empty strings split to [""], length matches, seg matches ""==""
        assert matches("", "") is True

    def test_wildcard_reference_table_from_readme(self):
        # user.*
        assert matches("user.*", "user.created") is True
        assert matches("user.*", "user.deleted") is True
        assert matches("user.*", "user.role.changed") is False
        assert matches("user.*", "user") is False

        # user.**
        assert matches("user.**", "user.created") is True
        assert matches("user.**", "user.role.changed") is True
        assert matches("user.**", "user") is False
        assert matches("user.**", "order.created") is False

        # *.created
        assert matches("*.created", "user.created") is True
        assert matches("*.created", "order.created") is True
        assert matches("*.created", "user.deleted") is False

        # **
        assert matches("**", "user") is True
        assert matches("**", "user.created") is True
        assert matches("**", "a.b.c") is True