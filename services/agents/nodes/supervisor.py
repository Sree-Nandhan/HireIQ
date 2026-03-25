from agents.state import AgentState

# The fixed pipeline execution order.
PIPELINE_ORDER = [
    "resume_parser",
    "jd_analyst",
    "company_researcher",
    "gap_analyst",
    "resume_tailor",
    "cover_letter",
    "interview_coach",
    "ats_scorer",
]


def supervisor_node(state: AgentState) -> AgentState:
    """Route to the next agent in the pipeline based on completed_agents.

    Short-circuits to END immediately if any agent has set state["error"],
    preventing cascading LLM calls after a failure and preserving the
    original root-cause error.

    Iterates through the fixed PIPELINE_ORDER and returns the first agent
    that has not yet been recorded in state["completed_agents"]. Sets
    state["next_agent"] to that agent name, or "END" when all agents have run.
    """
    # Short-circuit immediately if any agent has set an error.
    if state.get("error"):
        return {
            **state,
            "next_agent": "END",
        }

    completed = set(state.get("completed_agents", []))

    for agent in PIPELINE_ORDER:
        if agent not in completed:
            return {
                **state,
                "next_agent": agent,
            }

    # All agents have completed — signal the graph to terminate.
    return {
        **state,
        "next_agent": "END",
    }
