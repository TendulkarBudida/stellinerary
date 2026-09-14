"""
Context & Story Agent.

LLM-backed agent that takes an event/object and generates a short, scientifically
accurate, and awe-inspiring narrative blurb. The goal is to provide context so the
user isn't just looking at a "fuzzy dot" or a "streak of light," but understands
the scale, distance, and physics of what they're seeing.
"""

import logging
from typing import Optional

from app.models import CelestialEvent, ObjectStory
from app.services.llm_client import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert astronomer and science communicator, similar to Carl Sagan or Neil deGrasse Tyson.
Your goal is to explain celestial objects to amateur stargazers. You must provide a short narrative that evokes awe and gives true scale/context.

Guidelines:
1. Keep it short (3-4 sentences max for the story).
2. Include a distinct "Fun Fact" (1 sentence).
3. Be 100% scientifically accurate.
4. If it's a meteor shower, explain the parent body (comet/asteroid) and how fast the particles hit the atmosphere.
5. If it's a deep sky object or planet, emphasize the distance, time delay of light, or sheer size.
"""


async def generate_story_for_event(event: CelestialEvent) -> ObjectStory:
    """
    Generate an engaging story/context blurb for a specific celestial event.

    Args:
        event: The celestial event to explain.

    Returns:
        ObjectStory with the generated narrative. If the LLM fails, returns a
        fallback ObjectStory using the event's built-in description.
    """
    prompt = f"""Generate an observation guide for: {event.name}

Event Type: {event.type}
Description: {event.description}
"""
    
    if event.parent_body:
        prompt += f"Parent Body: {event.parent_body}\n"
    if event.speed_km_s:
        prompt += f"Speed: {event.speed_km_s} km/s\n"
    if event.target_object:
        prompt += f"Target Object: {event.target_object}\n"

    prompt += "\nRespond with EXACTLY the following format:\nSTORY: [3-4 sentence awe-inspiring narrative]\nFUN FACT: [1 sentence mind-blowing fact]\nPHYSICS: [1 sentence on the physics or distance]"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    try:
        response_text = await chat_completion(messages, temperature=0.7)
        return _parse_llm_response(response_text, event)
    except Exception as e:
        logger.error("Failed to generate story for %s: %s", event.name, e)
        # Graceful fallback using static data
        return ObjectStory(
            event_id=event.id,
            title=event.name,
            story_text=event.description or f"Observe the beauty of {event.name}.",
            fun_fact="The universe is vast and full of wonders.",
        )


def _parse_llm_response(text: str, event: CelestialEvent) -> ObjectStory:
    """Parse the formatted text from the LLM into an ObjectStory model."""
    lines = text.strip().split("\n")
    
    story = ""
    fun_fact = None
    physics = None
    
    # Simple parser for the expected output format
    current_section = "STORY"
    story_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("STORY:"):
            current_section = "STORY"
            story_lines.append(line[6:].strip())
        elif line.startswith("FUN FACT:"):
            current_section = "FUN FACT"
            fun_fact = line[9:].strip()
        elif line.startswith("PHYSICS:"):
            current_section = "PHYSICS"
            physics = line[8:].strip()
        else:
            if current_section == "STORY":
                story_lines.append(line)
            elif current_section == "FUN FACT" and fun_fact is not None:
                fun_fact += " " + line
            elif current_section == "PHYSICS" and physics is not None:
                physics += " " + line
                
    if not story_lines:
        story = text  # Fallback if the LLM didn't follow formatting
    else:
        story = " ".join(story_lines)
        
    return ObjectStory(
        event_id=event.id,
        title=event.name,
        story_text=story,
        fun_fact=fun_fact,
        physics_note=physics
    )
