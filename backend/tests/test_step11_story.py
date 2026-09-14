"""Step 11 — Context & Story agent tests.

Validates:
1. LLM response parsing works correctly.
2. Graceful fallback on LLM failure.
3. Prompt formatting includes event details.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.story import generate_story_for_event, _parse_llm_response
from app.models import CelestialEvent
from datetime import date


@pytest.fixture
def sample_event():
    return CelestialEvent(
        id="geminids_test",
        name="Geminid Meteor Shower",
        type="meteor_shower",
        peak_date=date(2026, 12, 14),
        active_start=date(2026, 12, 4),
        active_end=date(2026, 12, 20),
        description="A beautiful shower.",
        speed_km_s=35,
        parent_body="Asteroid 3200 Phaethon"
    )


class TestStoryAgent:
    def test_parse_llm_response_perfect_format(self, sample_event):
        llm_text = (
            "STORY: You are watching debris from an asteroid hitting the atmosphere. It is beautiful.\n"
            "FUN FACT: These meteors are traveling at 35 km/s.\n"
            "PHYSICS: The light is actually superheated compressed air, not the rock burning."
        )
        
        story = _parse_llm_response(llm_text, sample_event)
        
        assert story.event_id == "geminids_test"
        assert story.title == "Geminid Meteor Shower"
        assert "watching debris" in story.story_text
        assert "35 km/s" in story.fun_fact
        assert "superheated compressed air" in story.physics_note

    def test_parse_llm_response_messy_format(self, sample_event):
        llm_text = (
            "Here is your information:\n\n"
            "STORY: It is a great shower.\n"
            "It has many colors.\n\n"
            "FUN FACT: Asteroid 3200 Phaethon is essentially a dead comet.\n"
            "PHYSICS: Kinetic energy turns into heat."
        )
        
        story = _parse_llm_response(llm_text, sample_event)
        
        assert "It is a great shower. It has many colors." in story.story_text
        assert "dead comet" in story.fun_fact
        assert "Kinetic energy" in story.physics_note

    def test_parse_llm_response_fallback_format(self, sample_event):
        llm_text = "The Geminids are really cool to watch."
        
        story = _parse_llm_response(llm_text, sample_event)
        
        assert story.story_text == "The Geminids are really cool to watch."
        assert story.fun_fact is None
        assert story.physics_note is None

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_llm_failure(self, sample_event):
        with patch("app.agents.story.chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("API down")
            
            story = await generate_story_for_event(sample_event)
            
            assert story.story_text == sample_event.description
            assert story.fun_fact == "The universe is vast and full of wonders."
            
    @pytest.mark.asyncio
    async def test_successful_llm_call(self, sample_event):
        mock_response = (
            "STORY: A great story.\n"
            "FUN FACT: A fun fact.\n"
            "PHYSICS: Some physics."
        )
        with patch("app.agents.story.chat_completion", new_callable=AsyncMock, return_value=mock_response) as mock_chat:
            story = await generate_story_for_event(sample_event)
            
            mock_chat.assert_called_once()
            
            # Ensure the prompt contains the specific event details
            call_args = mock_chat.call_args[0][0]
            user_prompt = call_args[1]["content"]
            assert "Geminid Meteor Shower" in user_prompt
            assert "35 km/s" in user_prompt
            assert "Asteroid 3200 Phaethon" in user_prompt
            
            assert story.story_text == "A great story."
            assert story.fun_fact == "A fun fact."
