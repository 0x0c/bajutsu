"""Authoring agent abstraction (Tier 1).

The agent proposes the next action from an observation. The record loop executes
proposals to advance the app and writes out a deterministic scenario. Keeping the
agent behind a protocol lets the loop be tested with a scripted fake; the Claude
implementation lives in agents/claude.py.
"""

from .agent import Agent
from .enrichment_agent import EnrichmentAgent
from .enrichment_proposal import EnrichmentProposal
from .observation import Observation
from .proposal import HumanValueClass, Proposal
from .step_context import StepContext

__all__ = [
    "Agent",
    "EnrichmentAgent",
    "EnrichmentProposal",
    "HumanValueClass",
    "Observation",
    "Proposal",
    "StepContext",
]
