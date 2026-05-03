"""
agent.py
Builds and returns the LangChain job-search AgentExecutor with LangSmith tracing.
"""

import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langsmith import Client as LangSmithClient

from integrations.tools import ALL_TOOLS
from agent.prompts import JOB_SEARCH_SYSTEM_PROMPT


def configure_langsmith():
    """
    Enable LangSmith tracing if credentials are present.
    Returns True if tracing is active.
    """
    key     = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "job-search-agent")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    if key and tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"]     = project
        return True
    return False


def build_agent(profile: dict, temperature: float = 0) -> AgentExecutor:
    """
    Construct a LangChain OpenAI-tools agent for job searching.

    Args:
        profile: Structured user profile dict from input_parser.
        temperature: LLM temperature (default 0 for deterministic searches).

    Returns:
        AgentExecutor ready to invoke.
    """
    tracing_active = configure_langsmith()

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        # LangSmith auto-instruments if env vars are set
    )

    system_msg = JOB_SEARCH_SYSTEM_PROMPT.format(profile=str(profile))

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=8,
        handle_parsing_errors=True,
        return_intermediate_steps=True,   # Needed for LangSmith step visibility
    )

    return executor, tracing_active