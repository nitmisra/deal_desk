import os
import json
from dotenv import load_dotenv

from src.graph import compile_graph
from src.state import AgentState

# Load environment variables
load_dotenv()


def process_rfp(rfp_data: dict):
    """Process an entire RFP document."""
    
    print("=" * 80)
    print(f"🚀 Processing RFP: {rfp_data['rfp_id']}")
    print(f"   Total questions: {len(rfp_data['questions'])}")
    print("=" * 80)
    
    # Initialize the graph
    graph = compile_graph()
    
    # Process each question
    final_answers = {}
    
    for i, question in enumerate(rfp_data["questions"], 1):
        print(f"\n{'='*80}")
        print(f"📝 Question {i}/{len(rfp_data['questions'])}: {question}")
        print(f"{'='*80}")
        
        # Initialize state for this question
        initial_state = AgentState(
            rfp_id=rfp_data["rfp_id"],
            questions=rfp_data["questions"],
            current_question_index=i - 1,
            current_question=question,
            iteration_count=0,
            max_iterations=3
        )
        
        # Run the graph
        try:
            final_state = graph.invoke(initial_state.dict())
            
            # Store the answer
            if final_state["grader_verdict"] == "PASS":
                final_answers[question] = final_state["drafted_answer"]
                print(f"\n✅ FINAL ANSWER: {final_state['drafted_answer']}")
            else:
                final_answers[question] = f"[REQUIRES HUMAN REVIEW] {final_state['drafted_answer']}"
                print(f"\n⚠️  REQUIRES HUMAN REVIEW: {final_state['drafted_answer']}")
        
        except Exception as e:
            print(f"\n❌ ERROR processing question: {e}")
            final_answers[question] = f"[ERROR] {str(e)}"
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 RFP PROCESSING SUMMARY")
    print("=" * 80)
    
    auto_answered = sum(1 for q, a in final_answers.items() if not a.startswith("["))
    requires_human = sum(1 for q, a in final_answers.items() if a.startswith("[REQUIRES"))
    errors = sum(1 for q, a in final_answers.items() if a.startswith("[ERROR]"))
    
    print(f"Total questions: {len(rfp_data['questions'])}")
    print(f"Auto-answered: {auto_answered}")
    print(f"Requires human: {requires_human}")
    print(f"Errors: {errors}")
    print(f"Human Intervention Rate: {(requires_human / len(rfp_data['questions'])) * 100:.1f}%")
    
    # Save results
    output_file = f"output_{rfp_data['rfp_id']}.json"
    with open(output_file, "w") as f:
        json.dump({
            "rfp_id": rfp_data["rfp_id"],
            "answers": final_answers
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return final_answers


if __name__ == "__main__":
    # Sample RFP data
    sample_rfp = {
        "rfp_id": "acme_corp_2026",
        "questions": [
            "Do you support Single Sign-On (SSO)? What protocols are supported?",
            "What is your uptime SLA for the Enterprise tier?",
            "What is your API rate limit for Enterprise customers?",
            "Are you SOC2 compliant?",
            "Where is your data hosted? Do you support EU data residency?"
        ]
    }
    
    # Process the RFP
    process_rfp(sample_rfp)