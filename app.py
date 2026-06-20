"""
Streamlit chatbot UI for the Onboarding RAG Bot.
Run: streamlit run app.py
"""

import streamlit as st
from rag_graph import ask

st.set_page_config(
    page_title="Meridian Investment Management Corporation Onboarding Assistant",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 Meridian Investment Management Corporation Onboarding Assistant")
st.caption(
    "Ask anything about team processes, tools, dev setup, deployments, or the architecture. "
    "Answers are grounded in the team knowledge base."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption(f"Sources: {', '.join(msg['sources'])}")

# Input
if prompt := st.chat_input("Ask a question about the team or setup..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            history = [
                (m["role"], m["content"])
                for m in st.session_state.messages[:-1]
            ]
            result = ask(prompt, chat_history=history)

        answer = result["answer"]
        sources = result["sources"]
        refused = result["refused"]

        st.markdown(answer)
        if sources:
            st.caption(f"Sources: {', '.join(sources)}")
            with st.expander("🔍 Retrieved context (reranked)"):
                for chunk, score in zip(result["context"], result["relevance_scores"]):
                    st.markdown(f"**Relevance score: {score:.3f}**")
                    st.text(chunk[:500] + ("..." if len(chunk) > 500 else ""))
                    st.divider()
        elif refused:
            st.caption("No relevant documents found in the knowledge base.")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
