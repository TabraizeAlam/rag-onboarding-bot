"""
15-question evaluation against the onboarding knowledge base.
Outputs a table with retrieval quality and faithfulness notes.

Run: python eval.py
"""

from rag_graph import ask

EVAL_QUESTIONS = [
    # Happy path — should retrieve well
    {"q": "How do I set up my local development environment?", "category": "Setup"},
    {"q": "What tools do I need to install before cloning a repo?", "category": "Setup"},
    {"q": "How do I configure AWS SSO?", "category": "Setup"},
    {"q": "What is the deployment process to production?", "category": "Deployment"},
    {"q": "How do I roll back a production deployment?", "category": "Deployment"},
    {"q": "What are the PR review requirements?", "category": "Process"},
    {"q": "What is the branching strategy the team uses?", "category": "Process"},
    {"q": "What is the incident severity classification?", "category": "Process"},
    {"q": "Who is the Engineering Manager?", "category": "Team"},
    {"q": "What Slack channels should I join as a new hire?", "category": "Onboarding"},
    # Edge cases — ambiguous or cross-document
    {"q": "What should I do in my first week?", "category": "Onboarding"},
    {"q": "How do I request access to Snowflake?", "category": "Tools"},
    {"q": "What databases does Acme use and where are they hosted?", "category": "Architecture"},
    # Out-of-scope — should trigger refusal
    {"q": "What is the company stock price?", "category": "Out-of-scope"},
    {"q": "Can you write me a Python function to sort a list?", "category": "Out-of-scope"},
]


def run_eval():
    print(f"{'#':<3} {'Category':<15} {'Retrieved':<10} {'Refused':<8} Question")
    print("-" * 90)

    results = []
    for i, item in enumerate(EVAL_QUESTIONS, 1):
        result = ask(item["q"])
        refused = result["refused"]
        n_docs = result["num_docs_retrieved"]
        sources = ", ".join(result["sources"]) if result["sources"] else "—"

        tag = "REFUSED" if refused else f"{n_docs} docs"
        print(f"{i:<3} {item['category']:<15} {tag:<10} {str(refused):<8} {item['q'][:60]}")
        results.append({**item, **result})

    print("\n" + "=" * 90)
    print("ANSWERS\n")
    for i, r in enumerate(results, 1):
        print(f"Q{i}: {r['q']}")
        print(f"A:  {r['answer'][:300]}{'...' if len(r['answer']) > 300 else ''}")
        print(f"Sources: {', '.join(r['sources']) or 'none'}")
        print()

    refused_count = sum(1 for r in results if r["refused"])
    answered_count = len(results) - refused_count
    oos = [r for r in results if r["category"] == "Out-of-scope"]
    correct_refusals = sum(1 for r in oos if r["refused"])

    print("=" * 90)
    print("SUMMARY")
    print(f"  Total questions:       {len(results)}")
    print(f"  Answered:              {answered_count}")
    print(f"  Refused (no docs):     {refused_count}")
    print(f"  Correct refusals:      {correct_refusals}/{len(oos)} out-of-scope questions")


if __name__ == "__main__":
    run_eval()
