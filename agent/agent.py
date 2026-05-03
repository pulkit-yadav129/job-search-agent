"""
agent.py
Builds and returns the LangChain job-search AgentExecutor with LangSmith tracing.
"""

import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langchain.agents.agent import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # ✅ FIXED

from integrations.tools import ALL_TOOLS
from agent.prompts import JOB_SEARCH_SYSTEM_PROMPT


def configure_langsmith():
    key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "job-search-agent")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    if key and tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = project
        return True
    return False


def build_agent(profile: dict, temperature: float = 0):
    tracing_active = configure_langsmith()

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
    )

    # ✅ FIX: include profile as a variable in prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", JOB_SEARCH_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(
        llm=llm,
        tools=ALL_TOOLS,
        prompt=prompt
    )

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=8,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )

    return executor, tracing_active  # ✅ FIXED typo