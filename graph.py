from typing import Literal
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    router_node,
    retriever_node,
    generator_node,
    grader_node,
    human_intervention_node
)


def should_continue(state: AgentState) -> Literal["continue", "retry", "human_intervention", "complete"]:
    """Determine the next step based on grader verdict and iteration count."""
    
    if state.grader_verdict == "PASS":
        print("✅ Grader PASSED - moving to next question")
        return "complete"
    
    # Check if we need human intervention
    if state.failure_category == "MISSING_CONTEXT":
        print("⚠️  Missing context - escalating to human")
        return "human_intervention"
    
    if state.iteration_count >= state.max_iterations:
        print(f"⚠️  Max iterations ({state.max_iterations}) reached - escalating to human")
        return "human_intervention"
    
    print(f"🔄 Grader FAILED - retrying (attempt {state.iteration_count}/{state.max_iterations})")
    return "retry"


def build_graph() -> StateGraph:
    """Build the LangGraph state machine."""
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("grader", grader_node)
    workflow.add_node("human_intervention", human_intervention_node)
    
    # Define edges
    workflow.set_entry_point("router")
    
    workflow.add_edge("router", "retriever")
    workflow.add_edge("retriever", "generator")
    workflow.add_edge("generator", "grader")
    
    # Add conditional edges from grader
    workflow.add_conditional_edges(
        "grader",
        should_continue,
        {
            "retry": "generator",  # Loop back to generator
            "human_intervention": "human_intervention",
            "complete": END
        }
    )
    
    # After human intervention, go back to generator with human feedback
    workflow.add_edge("human_intervention", "generator")
    
    return workflow


def compile_graph():
    """Compile the graph for execution."""
    workflow = build_graph()
    return workflow.compile()