from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from .state import AgentState
from .vector_db import MockVectorDB
from .prompts import ROUTER_PROMPT, GENERATOR_PROMPT, GRADER_PROMPT

# Initialize LLMs
router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
generator_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
grader_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Initialize Vector DB
vector_db = MockVectorDB()


def router_node(state: AgentState) -> Dict[str, Any]:
    """Categorizes the question and determines which knowledge base to query."""
    print(f"\n🔀 [ROUTER] Categorizing question: {state.current_question[:50]}...")
    
    question = state.current_question
    prompt = ROUTER_PROMPT.format(question=question)
    
    response = router_llm.invoke([HumanMessage(content=prompt)])
    category = response.content.strip().upper()
    
    print(f"   → Category: {category}")
    
    return {"question_category": category}


def retriever_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves relevant context from the Vector DB with metadata filtering."""
    print(f"\n🔍 [RETRIEVER] Searching for relevant documents...")
    
    question = state.current_question
    category = state.question_category
    
    # Build metadata filter based on category
    metadata_filter = {"classification": "public"}
    
    if category == "SECURITY":
        metadata_filter["doc_type"] = ["security_whitepaper", "compliance_policy"]
    elif category == "PRICING":
        metadata_filter["doc_type"] = ["pricing_sheet"]
    elif category == "INFRASTRUCTURE":
        metadata_filter["doc_type"] = ["compliance_policy"]
    
    # Query Vector DB
    results = vector_db.query(
        query_text=question,
        metadata_filter=metadata_filter,
        top_k=3
    )
    
    print(f"   → Retrieved {len(results)} documents")
    for i, doc in enumerate(results, 1):
        print(f"     {i}. {doc['id']} (score: {doc['score']:.2f})")
    
    return {"retrieved_context": results}


def generator_node(state: AgentState) -> Dict[str, Any]:
    """Drafts an answer using the retrieved context."""
    print(f"\n✍️  [GENERATOR] Drafting response...")
    
    question = state.current_question
    context = "\n\n".join([doc["text"] for doc in state.retrieved_context])
    
    # Add human feedback if available
    human_feedback_section = ""
    if state.human_feedback:
        human_feedback_section = f"""
Human Expert Feedback (incorporate this into your answer):
{state.human_feedback}
"""
    
    prompt = GENERATOR_PROMPT.format(
        question=question,
        context=context,
        human_feedback_section=human_feedback_section
    )
    
    response = generator_llm.invoke([HumanMessage(content=prompt)])
    drafted_answer = response.content.strip()
    
    print(f"   → Draft: {drafted_answer[:100]}...")
    
    return {
        "drafted_answer": drafted_answer,
        "iteration_count": state.iteration_count + 1
    }


def grader_node(state: AgentState) -> Dict[str, Any]:
    """Evaluates the drafted answer for accuracy and groundedness."""
    print(f"\n⚖️  [GRADER] Evaluating draft (iteration {state.iteration_count})...")
    
    question = state.current_question
    context = "\n\n".join([doc["text"] for doc in state.retrieved_context])
    drafted_answer = state.drafted_answer
    
    prompt = GRADER_PROMPT.format(
        question=question,
        context=context,
        drafted_answer=drafted_answer
    )
    
    response = grader_llm.invoke([HumanMessage(content=prompt)])
    
    # Parse JSON response
    try:
        # Extract JSON from response (in case LLM adds markdown)
        json_str = response.content
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        
        grader_result = json.loads(json_str.strip())
        
        verdict = grader_result.get("verdict", "FAIL")
        reasoning = grader_result.get("reasoning", "")
        evidence = grader_result.get("extracted_evidence", [])
        failure_category = grader_result.get("failure_category", "UNKNOWN")
        
        print(f"   → Verdict: {verdict}")
        if verdict == "FAIL":
            print(f"   → Failure: {failure_category}")
            print(f"   → Reasoning: {reasoning[:150]}...")
        
        return {
            "grader_verdict": verdict,
            "grader_reasoning": reasoning,
            "extracted_evidence": evidence,
            "failure_category": failure_category if verdict == "FAIL" else None
        }
    
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Failed to parse grader response: {e}")
        return {
            "grader_verdict": "FAIL",
            "grader_reasoning": f"Failed to parse grader JSON: {str(e)}",
            "extracted_evidence": [],
            "failure_category": "GRADER_ERROR"
        }


def human_intervention_node(state: AgentState) -> Dict[str, Any]:
    """Flags the question for human review."""
    print(f"\n🚨 [HITL] Question requires human intervention!")
    print(f"   Question: {state.current_question}")
    print(f"   Reason: {state.failure_category}")
    print(f"   Agent's best attempt: {state.drafted_answer[:100]}...")
    
    # In production, this would:
    # 1. Save state to database
    # 2. Send Slack notification
    # 3. Wait for human input
    # For demo, we'll simulate human input
    print("\n💡 [SIMULATION] Human provides feedback...")
    
    # Simulate human providing the correct answer
    simulated_human_feedback = "Our API rate limit for Enterprise tier is 100,000 requests per hour."
    print(f"   Human feedback: {simulated_human_feedback}")
    
    return {
        "requires_human": True,
        "human_feedback": simulated_human_feedback
    }