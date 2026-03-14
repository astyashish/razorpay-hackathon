import asyncio
from langgraph.graph import StateGraph, END
from src.state import NexusState
from src.agents.scout import run_scout_agent
from src.agents.finder import run_finder_agent
from src.agents.writer import run_writer_agent
from src.agents.closer import run_closer_agent

def build_nexus_graph(log_queue=None):
    """Build the 4-agent NexusAI LangGraph pipeline."""
    
    graph = StateGraph(NexusState)
    
    async def make_log_fn(session_id):
        async def log_fn(msg):
            if log_queue and session_id:
                await log_queue.put({"session_id": session_id, "message": msg})
            print(f"[{session_id}] {msg}")
        return log_fn
    
    async def scout_node(state: NexusState) -> dict:
        log_fn = await make_log_fn(state.get("session_id", "default"))
        profile = await run_scout_agent(state["company_name"], log_fn)
        return {
            "profile": profile,
            "signals": profile.get("signals", []),
            "icp_score": profile.get("icp_score"),
            "confidence_scores": {
                k: v for k, v in profile.items() if k.endswith("_confidence")
            }
        }
    
    async def finder_node(state: NexusState) -> dict:
        log_fn = await make_log_fn(state.get("session_id", "default"))
        contact = await run_finder_agent(state["profile"], log_fn)
        return {"contact": contact}
    
    async def writer_node(state: NexusState) -> dict:
        log_fn = await make_log_fn(state.get("session_id", "default"))
        email_content = await run_writer_agent(state["profile"], state["contact"], log_fn)
        return {
            "email_variant_a": email_content.get("variant_a"),
            "email_variant_b": email_content.get("variant_b"),
            "subject_a": email_content.get("subject_a"),
            "subject_b": email_content.get("subject_b"),
            "score_a": email_content.get("score_a"),
            "score_b": email_content.get("score_b"),
            "winner_variant": email_content.get("winner"),
            "winner_reasoning": email_content.get("winner_reasoning"),
            "best_email": email_content.get("best_email"),
            "best_subject": email_content.get("best_subject"),
            "html_card": email_content.get("html_card")
        }
    
    async def closer_node(state: NexusState) -> dict:
        log_fn = await make_log_fn(state.get("session_id", "default"))
        email_content = {
            "best_email": state.get("best_email"),
            "best_subject": state.get("best_subject"),
            "html_card": state.get("html_card"),
            "winner": state.get("winner_variant"),
            "score_a": state.get("score_a"),
            "score_b": state.get("score_b")
        }
        result = await run_closer_agent(state["contact"], email_content, state["profile"], log_fn)
        return {"send_result": result}
    
    def should_continue_after_finder(state: NexusState) -> str:
        contact = state.get("contact", {})
        if not contact.get("email"):
            return "skip_closer"
        return "write"
    
    graph.add_node("scout", scout_node)
    graph.add_node("finder", finder_node)
    graph.add_node("writer", writer_node)
    graph.add_node("closer", closer_node)
    
    graph.set_entry_point("scout")
    graph.add_edge("scout", "finder")
    graph.add_conditional_edges("finder", should_continue_after_finder, {
        "write": "writer",
        "skip_closer": "writer"
    })
    graph.add_edge("writer", "closer")
    graph.add_edge("closer", END)
    
    return graph.compile()
