"""
15-question evaluation with LLM-judged faithfulness scoring.

For each answered question, a second LLM call (the "judge") checks whether
the answer is fully grounded in the retrieved chunks — the faithfulness
metric the project one-liner promises (>=90%).

Run: python eval.py
"""

import json
from rag_graph import ask, get_llm

EVAL_QUESTIONS = [
    # Setup and access
    {"q": "How do I set up my local dbt environment to connect to Snowflake?", "category": "Setup"},
    {"q": "What tools do I need to install as a new data developer?", "category": "Setup"},
    {"q": "How do I get access to Databricks?", "category": "Setup"},
    {"q": "Where do I request Snowflake access for the CONFIDENTIAL data role?", "category": "Setup"},
    # Platform and architecture
    {"q": "What are the Bronze, Silver, and Gold layers in the data platform?", "category": "Architecture"},
    {"q": "What is the medallion architecture?", "category": "Architecture"},
    {"q": "Which cloud does AIMCo's data platform run on?", "category": "Architecture"},
    # Pipeline workflow
    {"q": "What is the branching strategy and how do I name my feature branch?", "category": "Pipeline"},
    {"q": "What needs to happen before a new pipeline can go to production?", "category": "Pipeline"},
    {"q": "How do dbt models get deployed to production?", "category": "Pipeline"},
    # Governance and tools
    {"q": "What is Atlan used for and what do I need to do there?", "category": "Governance"},
    {"q": "How do I write a Soda data quality check?", "category": "Governance"},
    {"q": "What should I do in my first week as a new team member?", "category": "Onboarding"},
    # Out-of-scope — should trigger refusal
    {"q": "What is AIMCo's current portfolio return this quarter?", "category": "Out-of-scope"},
    {"q": "What is the weather forecast for Edmonton tomorrow?", "category": "Out-of-scope"},
]

JUDGE_PROMPT = """You are evaluating a RAG system for faithfulness.

Question: {question}

Retrieved context:
{context}

Generated answer:
{answer}

Is every factual claim in the answer supported by the retrieved context?
Respond with ONLY a JSON object: {{"faithful": true/false, "reason": "<one sentence>"}}"""


def judge_faithfulness(question: str, context: list[str], answer: str) -> dict:
    llm = get_llm(temperature=0.0)
    prompt = JUDGE_PROMPT.format(
        question=question,
        context="\n---\n".join(context),
        answer=answer,
    )
    raw = llm.invoke(prompt).content.strip()
    try:
        # Tolerate code fences around the JSON
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"faithful": None, "reason": f"Judge output unparseable: {raw[:100]}"}


def run_eval():
    print(f"{'#':<3} {'Category':<15} {'Docs':<6} {'Refused':<8} {'Faithful':<9} Question")
    print("-" * 100)

    results = []
    for i, item in enumerate(EVAL_QUESTIONS, 1):
        result = ask(item["q"])
        refused = result["refused"]

        if refused:
            faithful = "—"
            verdict = {}
        else:
            verdict = judge_faithfulness(item["q"], result["context"], result["answer"])
            faithful = str(verdict.get("faithful"))

        print(f"{i:<3} {item['category']:<15} {result['num_docs_retrieved']:<6} "
              f"{str(refused):<8} {faithful:<9} {item['q'][:55]}")
        results.append({**item, **result, "verdict": verdict})

    print("\n" + "=" * 100)
    print("ANSWERS\n")
    for i, r in enumerate(results, 1):
        print(f"Q{i}: {r['q']}")
        print(f"A:  {r['answer'][:300]}{'...' if len(r['answer']) > 300 else ''}")
        print(f"Sources: {', '.join(r['sources']) or 'none'}")
        if r["verdict"]:
            print(f"Judge: faithful={r['verdict'].get('faithful')} — {r['verdict'].get('reason', '')}")
        print()

    # Summary
    oos = [r for r in results if r["category"] == "Out-of-scope"]
    in_scope = [r for r in results if r["category"] != "Out-of-scope"]
    answered = [r for r in in_scope if not r["refused"]]
    judged = [r for r in answered if r["verdict"].get("faithful") is not None]
    faithful_count = sum(1 for r in judged if r["verdict"]["faithful"])
    correct_refusals = sum(1 for r in oos if r["refused"])

    print("=" * 100)
    print("SUMMARY")
    print(f"  In-scope questions answered:  {len(answered)}/{len(in_scope)}")
    print(f"  Correct refusals:             {correct_refusals}/{len(oos)} out-of-scope questions")
    if judged:
        pct = 100 * faithful_count / len(judged)
        print(f"  Faithfulness:                 {faithful_count}/{len(judged)} = {pct:.0f}%  (target: >=90%)")


if __name__ == "__main__":
    run_eval()
