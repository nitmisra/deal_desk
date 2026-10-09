# deal_desk
# Agentic RFP & Proposal Response System

> **A production-grade, Agentic AI architecture for automating complex enterprise RFP responses, featuring advanced Vector DB context management, self-correcting LLM-as-a-Judge evals, and asynchronous Human-in-the-Loop (HITL) mechanics.**

---

## 📖 Overview

Enterprise Account Executives spend hundreds of hours manually answering complex, 50-to-100-question Requests for Proposals (RFPs). **DealDesk** is an Agentic AI system designed to autonomously ingest RFPs, research answers across internal knowledge bases, draft compliant responses, and seamlessly escalate edge-cases to human experts.

This repository serves as the architectural blueprint, product strategy, and implementation guide for building a robust, eval-driven Agentic AI product. It moves beyond naive RAG (Retrieval-Augmented Generation) to solve real-world enterprise challenges: context-window limits, hallucinations, outdated information, and the need for human trust.

---

## 🏗️ High-Level Architecture & Approach

DealDesk is not a simple "prompt-in, answer-out" chatbot. It is built as a **State Machine** using an Agentic framework (e.g., LangGraph). 

### The User Journey
1. **Ingestion:** AE uploads a 60-question RFP. The system parses and extracts discrete questions.
2. **Triage:** The Agent categorizes questions and flags "Red" (low confidence/missing context) vs "Green" (high confidence) questions.
3. **Autonomous Drafting:** The Agent searches internal Vector DBs, drafts answers, and grades its own work.
4. **Human-in-the-Loop (HITL):** For "Red" questions, the system asynchronously pauses, alerts a Subject Matter Expert (SME) via Slack/UI, and incorporates their feedback.
5. **Export:** A perfectly formatted, compliant document is generated.

---

## 🧩 Core Components & Design Decisions

### 1. Vector DB Context Management
**The Challenge:** Naive RAG (splitting text into 500-character chunks) destroys tables, breaks context, and retrieves outdated information. Pure "Chunkless" (document-level) retrieval blows up token costs and suffers from the "Lost in the Middle" phenomenon.

**The Selected Path: Hybrid Document-Level Retrieval with Contextual Compression**
Instead of naive chunking, we retrieve entire documents (or large structural sections) and use a lightweight LLM to compress them before final generation.

*   **Metadata Filtering:** Every document is tagged with `effective_date`, `expiration_date`, `doc_type`, and `classification`. The Retriever hard-filters out expired or `internal_only` docs *before* vector search.
*   **Parent-Child / Structural Chunking:** When chunking is necessary, we use structural parsing (Markdown/HTML) and map small child chunks (for precise embedding) to large parent chunks (for full context).

#### Pros & Cons
| Approach | Pros | Cons |
| :--- | :--- | :--- |
| **Naive Chunking** | Low token cost, fast retrieval. | Breaks tables, loses context, high hallucination risk. |
| **Pure Chunkless** | Perfect context integrity, zero chunking engineering. | Massive token costs, high latency, "Lost in the Middle" errors. |
| **Hybrid (Selected)** | Preserves tables/context, highly precise, cost-controlled. | Requires a slightly more complex ingestion and compression pipeline. |

**Why this path was selected:** It provides the context integrity of chunkless retrieval (crucial for complex pricing tables and compliance matrices) while using LLM-based compression to keep token costs and latency within production limits.

---

### 2. The Agentic State Machine
**The Challenge:** LLMs are non-deterministic. A single prompt cannot reliably handle a 60-question RFP without getting confused or hallucinating.

**The Selected Path: Node-Based State Machine with Conditional Edges**
We use a framework like LangGraph to define explicit `Nodes` (actions) and `Edges` (logic).

*   **Nodes:** `Router` (categorizes question), `Retriever` (fetches context), `Generator` (drafts answer), `Grader` (evaluates draft).
*   **The Agentic Loop:** If the Grader fails the draft, a conditional edge routes the state *back* to the Router/Generator with the Grader's feedback injected into the prompt, allowing the agent to self-correct up to `max_iterations` (e.g., 3 times).

#### Pros & Cons
| Approach | Pros | Cons |
| :--- | :--- | :--- |
| **Single Prompt (Zero-shot)** | Extremely fast, cheap, easy to build. | Fails on complex tasks, no self-correction, high hallucination. |
| **State Machine (Selected)** | Self-correcting, highly observable, modular. | Higher latency, higher API costs, complex state management. |

**Why this path was selected:** Enterprise RFPs require high accuracy. The self-correcting loop mimics human problem-solving, drastically reducing the final error rate before a human ever sees the output.

---

### 3. Evals: The Un-Trickable Grader Node
**The Challenge:** LLMs suffer from "sycophancy." If you ask an LLM to grade its own work using a naive prompt ("Is this a good answer?"), it will almost always say yes.

**The Selected Path: Adversarial LLM-as-a-Judge with Forced Evidence Extraction**
We strip the LLM of its "helpful assistant" persona and prompt it as a "ruthless compliance auditor."

*   **Closed Book Rule:** The Grader is explicitly forbidden from using its pre-trained knowledge.
*   **Forced Evidence:** The Grader *must* output exact, verbatim quotes from the retrieved context that support the draft. If it cannot find quotes, it must fail the draft.
*   **Chain of Thought:** The Grader must output its reasoning in JSON *before* outputting the final `PASS/FAIL` verdict.

#### Pros & Cons
| Approach | Pros | Cons |
| :--- | :--- | :--- |
| **Naive Grading** | Simple to implement. | High false-positive rate, easily tricked by confident hallucinations. |
| **Adversarial + Evidence (Selected)** | Catches subtle hallucinations, provides audit trails, highly reliable. | Slower (requires JSON parsing and CoT), requires careful prompt engineering. |

**Why this path was selected:** In enterprise sales, a hallucinated answer (e.g., inventing a security compliance cert) can lose a deal or cause legal liability. Forced evidence extraction mathematically grounds the evaluation, making it production-safe.

### Building the Eval Suite
Evaluating an agent is much harder than evaluating a simple chatbot. You need to measure the journey, not just the destination. You will use a tool like LangSmith, Braintrust, or Arize Phoenix to build three layers of evals:
1. Retrieval Evals (Did it find the right info?)
Context Precision: Out of all the documents the agent retrieved for Question #5, how many were actually relevant?
Context Recall: Did the agent miss a critical document that should have been retrieved? (You will need a "golden dataset" of the exact documents required for 50 sample RFP questions to test this).
2. Trajectory / Agentic Evals (Did it act rationally?)
Tool Routing Accuracy: Did the agent correctly identify that a pricing question should use the SQL Tool instead of the Product Docs Vector DB?
Step Efficiency: Did the agent solve the question in 2 steps, or did it get stuck in a loop and take 8 steps? (Penalize unnecessary tool calls to save latency and API costs).
3. Final Output Evals (Is the answer good?)
Faithfulness (Hallucination Check): Use an "LLM-as-a-Judge" to verify that the final drafted answer is strictly supported by the retrieved context. If the context says "We support SSO," and the agent writes "We support SSO and MFA," it fails.
Tone & Formatting Compliance: Does the output match the strict, professional tone required for an enterprise RFP? Is it formatted in the exact JSON or Markdown structure requested?

---

### 4. Human-in-the-Loop (HITL) Mechanics
**The Challenge:** AI will never be 100% accurate. When the agent fails, holding the API connection open while a human answers is technically impossible and ruins UX.

**The Selected Path: Asynchronous State Persistence & Context-Rich Escalation**
When the Grader fails 3 times (or flags `MISSING_CONTEXT`), the State Machine triggers an `interrupt`.

1.  **Async Pause:** The state is serialized to a database. The agent goes to sleep (zero compute cost).
2.  **Context-Rich UI:** The human SME receives a Slack alert with a link to a UI showing the Question, the Agent's failed draft, the Grader's exact reason for failure, and the retrieved context.
3.  **Structured Input:** The human doesn't just type in a void; they can provide the answer, link a new document, or mark it N/A.
4.  **Synthesis & Resume:** The agent wakes up, uses an LLM to format the human's raw input into the enterprise tone, runs it through the Grader one last time, and completes the state.

#### Pros & Cons
| Approach | Pros | Cons |
| :--- | :--- | :--- |
| **Synchronous Blocking** | Simple to code. | Terrible UX, timeouts, wastes compute while waiting. |
| **Async HITL (Selected)** | Great UX, zero wasted compute, builds trust. | Requires robust state management (e.g., LangGraph checkpoints) and UI integration. |

**Why this path was selected:** It shifts the paradigm from "AI replacing humans" to "AI augmenting humans." Furthermore, every human correction is automatically saved to a "Golden Dataset," turning HITL into a flywheel for future automation.

---

## 🛠️ Recommended Tech Stack

To build this architecture, the following industry-standard stack is recommended:

*   **Agent Framework:** [LangGraph](https://github.com/langchain-ai/langgraph) (for state machine management, async interrupts, and checkpointing).
*   **Vector Database:** [Pinecone](https://www.pinecone.io/) or [Qdrant](https://qdrant.tech/) (for robust metadata filtering and hybrid search).
*   **Embeddings:** Cohere `embed-v3` (excellent for hybrid dense/sparse retrieval) or OpenAI `text-embedding-3-large`.
*   **LLMs:** 
    *   *Generator/Router:* Claude 3.5 Sonnet or GPT-4o (excellent at following complex instructions).
    *   *Compressor/Grader:* GPT-4o-mini or Claude 3.5 Haiku (fast, cheap, highly capable at structured JSON output).
*   **Observability & Evals:** [LangSmith](https://smith.langchain.com/) or [Braintrust](https://www.braintrustdata.com/) for tracing agent steps and running LLM-as-a-judge meta-evals.
*   **Ingestion/Parsing:** [Unstructured.io](https://unstructured.io/) for parsing complex PDFs and preserving tables.

---

## 📊 Product Metrics & Success Criteria

As a Product Manager, success is not measured by "zero human touch," but by efficient human augmentation. The following metrics will be tracked in the production dashboard:

1.  **Human Intervention Rate (HIR):** `(Questions requiring human help / Total questions)`. *Target: < 15% for mature systems.*
2.  **Agent Self-Correction Rate:** Of the questions that failed the first time, what percentage did the agent fix on its own during the retry loop? *Target: > 60%.*
3.  **Time-to-Resolve per HITL:** How long does the human take to answer an escalated question? *Target: < 60 seconds.*
4.  **Retrieval Precision/Recall:** Measured via a "Golden Dataset" of 50 manually verified RFP questions.

---



# Run the ingestion pipeline to populate the Vector DB
python src/ingest.py --data_path ./sample_knowledge_base/

# Run the agent on a sample RFP
python src/main.py --rfp_path ./sample_rfps/acme_corp_rfp.pdf
