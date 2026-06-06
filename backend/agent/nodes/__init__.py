"""Agent nodes package."""

from __future__ import annotations

import time

from langchain_ollama import ChatOllama
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.state import AgentState
from backend.core.retrieval.groundx_client import groundx_client
from backend.core.retrieval.qdrant_client import qdrant_retriever

from backend.agent.nodes.groundx import groundx_retrieve_node as _groundx_retrieve_node
from backend.agent.nodes.context import context_synthesis_node as _context_synthesis_node
from backend.agent.nodes.answer import answer_node as _answer_node
from backend.agent.nodes.ocr import ocr_node as _ocr_node
from backend.agent.nodes.qdrant import qdrant_retrieve_node as _qdrant_retrieve_node
from backend.agent.nodes.router import router_node as _router_node


async def router_node(state: AgentState, config: dict, session: AsyncSession) -> AgentState:
    _ = (config, session, ChatOllama, qdrant_retriever, groundx_client, time)
    return await _router_node(state, session=session, config=config)


async def groundx_retrieve_node(
    state: AgentState,
    config: dict,
    session: AsyncSession,
) -> AgentState:
    _ = (config, session, ChatOllama, qdrant_retriever, groundx_client, time)
    return await _groundx_retrieve_node(state)


async def qdrant_retrieve_node(
    state: AgentState,
    config: dict,
    session: AsyncSession,
) -> AgentState:
    _ = (config, session, ChatOllama, qdrant_retriever, groundx_client, time)
    return await _qdrant_retrieve_node(state)


async def ocr_node(state: AgentState, config: dict, session: AsyncSession) -> AgentState:
    _ = (config, ChatOllama, qdrant_retriever, groundx_client, time)
    return await _ocr_node(state, session=session)


async def context_synthesis_node(
    state: AgentState,
    config: dict,
    session: AsyncSession,
) -> AgentState:
    _ = (config, session, ChatOllama, qdrant_retriever, groundx_client, time)
    return await _context_synthesis_node(state)


async def answer_node(state: AgentState, config: dict, session: AsyncSession) -> AgentState:
    _ = (config, session, ChatOllama, qdrant_retriever, groundx_client, time)
    return await _answer_node(state)


__all__ = [
    "router_node",
    "groundx_retrieve_node",
    "qdrant_retrieve_node",
    "ocr_node",
    "context_synthesis_node",
    "answer_node",
]
