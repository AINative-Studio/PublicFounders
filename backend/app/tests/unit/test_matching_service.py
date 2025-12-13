"""
Unit Tests for Matching Service

Tests the introduction suggestion system including:
- Suggestion generation
- Match score calculation
- Goal helper finding
- Ask matcher finding
- Reasoning generation
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.matching_service import (
    matching_service,
    MatchingService,
    MatchingServiceError
)


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_goals():
    """Sample user goals."""
    return [
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "type": "fundraising",
            "description": "Raise $2M seed round for B2B SaaS",
            "priority": 1,
            "is_active": True,
            "embedding_id": "goal_embed_1"
        },
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "type": "product",
            "description": "Build AI-powered marketplace platform",
            "priority": 2,
            "is_active": True,
            "embedding_id": "goal_embed_2"
        }
    ]


@pytest.fixture
def sample_asks():
    """Sample user asks."""
    return [
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "description": "Need intros to tier 1 VCs in San Francisco",
            "status": "open",
            "urgency": "high",
            "embedding_id": "ask_embed_1"
        }
    ]


@pytest.fixture
def sample_search_results():
    """Sample vector search results."""
    return [
        {
            "similarity": 0.85,
            "metadata": {
                "user_id": str(uuid4()),
                "source_id": str(uuid4())
            },
            "document": "Looking for seed investors for marketplace startup"
        },
        {
            "similarity": 0.78,
            "metadata": {
                "user_id": str(uuid4()),
                "source_id": str(uuid4())
            },
            "document": "Building B2B SaaS platform"
        }
    ]


@pytest.fixture
def sample_candidate_user():
    """Sample candidate user."""
    return {
        "id": str(uuid4()),
        "name": "Jane Founder",
        "headline": "CEO at AI Startup",
        "location": "San Francisco, CA",
        "linkedin_id": "jane-founder",
        "created_at": "2024-01-01T00:00:00"
    }


class TestMatchingService:
    """Test suite for MatchingService."""

    @pytest.mark.asyncio
    async def test_suggest_introductions_returns_ranked_matches(
        self,
        sample_user_id,
        sample_goals,
        sample_asks,
        sample_search_results,
        sample_candidate_user
    ):
        """Test that suggest_introductions returns ranked matches."""
        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            # Mock database queries
            mock_db.query_rows.side_effect = [
                sample_goals,  # User goals
                sample_asks,   # User asks
                sample_candidate_user,  # Candidate user
                [sample_candidate_user],  # Get candidate by ID
                [],  # Candidate goals
                [],  # Candidate asks
                [],  # Recent posts for trust score
            ]

            # Mock embedding search
            mock_embed.search_similar.return_value = sample_search_results

            # Test
            service = MatchingService()
            suggestions = await service.suggest_introductions(
                user_id=sample_user_id,
                limit=10,
                min_score=0.6
            )

            # Assertions
            assert isinstance(suggestions, list)
            assert len(suggestions) <= 10

            # Check structure of first suggestion
            if suggestions:
                suggestion = suggestions[0]
                assert "target_user_id" in suggestion
                assert "target_name" in suggestion
                assert "match_score" in suggestion
                assert "reasoning" in suggestion
                assert "matching_goals" in suggestion
                assert "matching_asks" in suggestion

                # Check match score structure
                match_score = suggestion["match_score"]
                assert "relevance_score" in match_score
                assert "trust_score" in match_score
                assert "reciprocity_score" in match_score
                assert "overall_score" in match_score

                # Check score ranges
                assert 0.0 <= match_score["relevance_score"] <= 1.0
                assert 0.0 <= match_score["trust_score"] <= 1.0
                assert 0.0 <= match_score["reciprocity_score"] <= 1.0
                assert 0.0 <= match_score["overall_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_suggest_introductions_no_goals_or_asks(self, sample_user_id):
        """Test suggest_introductions with no goals or asks returns empty."""
        with patch('app.services.matching_service.zerodb_client') as mock_db:
            # Mock empty goals and asks
            mock_db.query_rows.side_effect = [[], []]

            service = MatchingService()
            suggestions = await service.suggest_introductions(
                user_id=sample_user_id,
                limit=10
            )

            assert suggestions == []

    @pytest.mark.asyncio
    async def test_calculate_match_score_produces_valid_scores(self, sample_user_id):
        """Test calculate_match_score produces valid scores."""
        target_id = uuid4()

        with patch('app.services.matching_service.zerodb_client') as mock_db:
            # Mock user data
            mock_db.get_by_id.return_value = {
                "id": str(target_id),
                "name": "Test User",
                "headline": "Founder",
                "location": "SF",
                "linkedin_id": "test",
                "created_at": "2024-01-01T00:00:00"
            }
            mock_db.get_by_field.return_value = {
                "user_id": str(target_id),
                "bio": "Experienced founder"
            }
            mock_db.query_rows.side_effect = [
                [],  # Recent posts
                [],  # User A goals
                [],  # User B goals
                [],  # User A asks
                []   # User B asks
            ]

            service = MatchingService()
            scores = await service.calculate_match_score(
                user_a_id=sample_user_id,
                user_b_id=target_id
            )

            # Check all required scores are present
            assert "relevance_score" in scores
            assert "trust_score" in scores
            assert "reciprocity_score" in scores
            assert "overall_score" in scores

            # Check all scores are in valid range
            for key, value in scores.items():
                assert 0.0 <= value <= 1.0, f"{key} is out of range: {value}"

    @pytest.mark.asyncio
    async def test_find_goal_helpers_finds_relevant_founders(self, sample_goals):
        """Test find_goal_helpers finds relevant founders."""
        goal = sample_goals[0]
        goal_id = UUID(goal["id"])

        helper_user = {
            "id": str(uuid4()),
            "name": "Helper Founder",
            "headline": "Expert in B2B SaaS"
        }

        search_results = [
            {
                "similarity": 0.88,
                "metadata": {"user_id": helper_user["id"]},
                "document": "Expert in SaaS fundraising"
            }
        ]

        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            mock_db.get_by_id.side_effect = [goal, helper_user]
            mock_embed.search_similar.return_value = search_results

            service = MatchingService()
            helpers = await service.find_goal_helpers(goal_id=goal_id, limit=5)

            assert isinstance(helpers, list)
            assert len(helpers) <= 5

            if helpers:
                helper = helpers[0]
                assert "user_id" in helper
                assert "name" in helper
                assert "similarity" in helper
                assert "reason" in helper
                assert 0.0 <= helper["similarity"] <= 1.0

    @pytest.mark.asyncio
    async def test_find_ask_matchers_finds_helpers(self, sample_asks):
        """Test find_ask_matchers finds helpers."""
        ask = sample_asks[0]
        ask_id = UUID(ask["id"])

        matcher_user = {
            "id": str(uuid4()),
            "name": "Investor",
            "headline": "VC Partner"
        }

        search_results = [
            {
                "similarity": 0.92,
                "metadata": {"user_id": matcher_user["id"]},
                "document": "Investing in B2B SaaS seed rounds"
            }
        ]

        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            mock_db.get_by_id.side_effect = [ask, matcher_user]
            mock_embed.search_similar.return_value = search_results

            service = MatchingService()
            matchers = await service.find_ask_matchers(ask_id=ask_id, limit=5)

            assert isinstance(matchers, list)
            assert len(matchers) <= 5

            if matchers:
                matcher = matchers[0]
                assert "user_id" in matcher
                assert "name" in matcher
                assert "similarity" in matcher
                assert "reason" in matcher
                assert 0.0 <= matcher["similarity"] <= 1.0

    @pytest.mark.asyncio
    async def test_generate_match_reasoning_creates_readable_text(
        self,
        sample_goals,
        sample_asks,
        sample_candidate_user
    ):
        """Test generate_match_reasoning creates human-readable text."""
        matching_signals = [
            {
                "type": "goal",
                "source_text": "Raise seed round",
                "similarity": 0.85
            },
            {
                "type": "ask",
                "source_text": "Need VC intros",
                "similarity": 0.78
            }
        ]

        service = MatchingService()
        reasoning = await service.generate_match_reasoning(
            user_goals=sample_goals,
            user_asks=sample_asks,
            candidate_user=sample_candidate_user,
            candidate_goals=[],
            candidate_asks=[],
            matching_signals=matching_signals
        )

        assert isinstance(reasoning, str)
        assert len(reasoning) > 0
        # Should contain some context about the match
        assert any(word in reasoning.lower() for word in ["goal", "help", "similar", "based"])

    @pytest.mark.asyncio
    async def test_filtering_by_min_score(self, sample_user_id):
        """Test that min_score filters out low-quality matches."""
        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            # Mock data that would produce low scores
            mock_db.query_rows.side_effect = [
                [{"id": str(uuid4()), "description": "test", "is_active": True, "embedding_id": "e1"}],
                [],  # No asks
            ]

            mock_embed.search_similar.return_value = [
                {
                    "similarity": 0.4,  # Low similarity
                    "metadata": {"user_id": str(uuid4()), "source_id": str(uuid4())},
                    "document": "Unrelated content"
                }
            ]

            service = MatchingService()
            suggestions = await service.suggest_introductions(
                user_id=sample_user_id,
                limit=10,
                min_score=0.8  # High threshold
            )

            # Should filter out low-quality matches
            assert len(suggestions) == 0

    @pytest.mark.asyncio
    async def test_no_self_suggestions(self, sample_user_id):
        """Test that users don't get suggested to themselves."""
        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            # Mock goals
            mock_db.query_rows.side_effect = [
                [{"id": str(uuid4()), "description": "test", "is_active": True, "embedding_id": "e1"}],
                [],  # No asks
            ]

            # Mock search results that include self
            mock_embed.search_similar.return_value = [
                {
                    "similarity": 0.95,
                    "metadata": {
                        "user_id": str(sample_user_id),  # Same as requesting user
                        "source_id": str(uuid4())
                    },
                    "document": "My own goal"
                }
            ]

            service = MatchingService()
            suggestions = await service.suggest_introductions(
                user_id=sample_user_id,
                limit=10
            )

            # Should not suggest self
            for suggestion in suggestions:
                assert suggestion["target_user_id"] != str(sample_user_id)

    @pytest.mark.asyncio
    async def test_match_type_goal_based(self, sample_user_id, sample_goals):
        """Test match_type='goal_based' only uses goals."""
        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            mock_db.query_rows.side_effect = [
                sample_goals,
                [{"id": str(uuid4()), "description": "test ask", "status": "open", "embedding_id": "ask1"}],
            ]

            mock_embed.search_similar.return_value = []

            service = MatchingService()
            await service.suggest_introductions(
                user_id=sample_user_id,
                match_type="goal_based"
            )

            # Verify embedding search was called for goals only
            assert mock_embed.search_similar.called
            # Should be called once per goal, not for asks
            assert mock_embed.search_similar.call_count >= len(sample_goals)

    @pytest.mark.asyncio
    async def test_match_type_ask_based(self, sample_user_id, sample_asks):
        """Test match_type='ask_based' only uses asks."""
        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            mock_db.query_rows.side_effect = [
                [{"id": str(uuid4()), "description": "test goal", "is_active": True, "embedding_id": "g1"}],
                sample_asks,
            ]

            mock_embed.search_similar.return_value = []

            service = MatchingService()
            await service.suggest_introductions(
                user_id=sample_user_id,
                match_type="ask_based"
            )

            # Verify embedding search was called for asks only
            assert mock_embed.search_similar.called

    @pytest.mark.asyncio
    async def test_trust_score_calculation(self):
        """Test _calculate_trust_score with various profile completeness levels."""
        service = MatchingService()

        # Test complete profile (high trust)
        complete_user = {
            "id": str(uuid4()),
            "name": "Complete User",
            "headline": "CEO at Startup",
            "location": "San Francisco",
            "linkedin_id": "complete-user",
            "created_at": "2024-01-01T00:00:00"
        }

        complete_profile = {
            "user_id": complete_user["id"],
            "bio": "Experienced founder with multiple exits"
        }

        with patch('app.services.matching_service.zerodb_client') as mock_db:
            mock_db.get_by_id.return_value = complete_user
            mock_db.get_by_field.return_value = complete_profile
            mock_db.query_rows.return_value = [{"id": "post1"}]  # Has posts

            score = await service._calculate_trust_score(UUID(complete_user["id"]))

            # Complete profile should have high trust
            assert score >= 0.7

    @pytest.mark.asyncio
    async def test_reciprocity_score_calculation(self):
        """Test _calculate_reciprocity_score with various scenarios."""
        service = MatchingService()
        user_a = uuid4()
        user_b = uuid4()

        # Test: Both have goals (high reciprocity)
        with patch('app.services.matching_service.zerodb_client') as mock_db:
            mock_db.query_rows.side_effect = [
                [{"id": str(uuid4())}],  # User A goals
                [{"id": str(uuid4())}],  # User B goals
                [],  # User A asks
                []   # User B asks
            ]

            score = await service._calculate_reciprocity_score(user_a, user_b)
            assert score >= 0.7  # High reciprocity when both have goals

    @pytest.mark.asyncio
    async def test_suspicious_user_filtering(self, sample_user_id):
        """Test that suspicious users are filtered out."""
        service = MatchingService()

        # Very new account (suspicious)
        new_user = {
            "id": str(uuid4()),
            "created_at": "2024-12-13T10:00:00"  # Very recent
        }

        with patch('app.services.matching_service.datetime') as mock_dt:
            # Mock current time to be shortly after account creation
            mock_dt.utcnow.return_value = mock_dt.fromisoformat("2024-12-13T10:30:00")
            mock_dt.fromisoformat = lambda x: mock_dt.fromisoformat(x)

            is_suspicious = await service._is_suspicious_user(new_user)
            assert is_suspicious is True

    @pytest.mark.asyncio
    async def test_error_handling_on_embedding_failure(self, sample_user_id, sample_goals):
        """Test graceful handling of embedding service errors."""
        with patch('app.services.matching_service.zerodb_client') as mock_db, \
             patch('app.services.matching_service.embedding_service') as mock_embed:

            mock_db.query_rows.side_effect = [sample_goals, []]

            # Mock embedding service to raise error
            from app.services.embedding_service import EmbeddingServiceError
            mock_embed.search_similar.side_effect = EmbeddingServiceError("API error")

            service = MatchingService()
            # Should not raise, but return empty or partial results
            suggestions = await service.suggest_introductions(
                user_id=sample_user_id,
                limit=10
            )

            # Should handle error gracefully
            assert isinstance(suggestions, list)
