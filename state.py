from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """The state object that flows through the agent graph."""
    
    # Input
    rfp_id: str
    questions: List[str] = Field(default_factory=list)
    current_question_index: int = 0
    
    # Processing
    current_question: str = ""
    question_category: Optional[str] = None
    retrieved_context: List[Dict[str, Any]] = Field(default_factory=list)
    drafted_answer: str = ""
    
    # Evaluation
    grader_reasoning: str = ""
    extracted_evidence: List[str] = Field(default_factory=list)
    grader_verdict: Optional[Literal["PASS", "FAIL"]] = None
    failure_category: Optional[str] = None
    
    # Control flow
    iteration_count: int = 0
    max_iterations: int = 3
    requires_human: bool = False
    human_feedback: Optional[str] = None
    
    # Output
    final_answers: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True