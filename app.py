import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from memory_manager import seed_hindsight_memory, recall_audit_context, get_all_past_audit_findings

load_dotenv()

# Setup Streamlit Page
st.set_page_config(page_title="SOC 2 Compliance Agent", page_icon="🛡️", layout="wide")
st.title("🛡️ Autonomous SOC 2 Compliance & Audit Agent")
st.caption("Powered by Hindsight Persistent Memory & Groq Llama-3")

# Sidebar for Memory Controls
with st.sidebar:
    st.header("⚙️ Memory Management")
    if st.button("📥 Seed Historical Audit Memory"):
        with st.spinner("Pushing past audit findings to Hindsight..."):
            msg = seed_hindsight_memory()
            st.success(msg)

    st.info("Hindsight Memory Bank: `soc2-compliance-bank`")

# Main Interface

# Summary Table of Past SOC 2 Audit Findings Stored in Memory
st.subheader("📋 Past SOC 2 Audit Findings (Stored in Memory)")
findings = get_all_past_audit_findings()

if findings:
    df_findings = pd.DataFrame(findings)
    st.dataframe(df_findings, use_container_width=True)
else:
    st.info("No past audit findings found in memory bank. Click '📥 Seed Historical Audit Memory' in the sidebar to populate memory.")

st.divider()

st.subheader("Simulate Operational Change / Event")
st.write("Enter an internal decision, incident, or schedule delay to check for audit risks:")

user_input = st.text_area(
    "Operational Log Input:",
    value="Engineering postponed the quarterly staging database disaster recovery test to next month due to sprint deadlines.",
    height=100
)

if st.button("🚨 Analyze Risk & Compliance Gaps"):
    if not user_input.strip():
        st.warning("Please enter an operational log.")
    else:
        col1, col2 = st.columns(2)

        # Step 1: Recall from Hindsight Memory
        with col1:
            st.markdown("### 🧠 Hindsight Memory Recall")
            with st.spinner("Searching past audit history & controls..."):
                recalled_memory = recall_audit_context(user_input)
                st.info(recalled_memory)

        # Step 2: Groq LLM Risk Synthesis
        with col2:
            st.markdown("### 🤖 Agent Risk Verdict")
            with st.spinner("Analyzing risk against audit history..."):
                groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

                system_prompt = f"""
                You are an expert Enterprise SOC 2 Lead Auditor.
                Analyze the user's operational log in light of the historical context retrieved from Hindsight memory.

                HISTORICAL AUDIT MEMORY (RECALLED):
                {recalled_memory}

                TASK:
                1. Identify if this log violates internal controls or repeats past audit findings.
                2. Highlight the specific Control ID and past finding year if applicable.
                3. Issue an Audit Risk Level (LOW, MEDIUM, HIGH, CRITICAL).
                4. Provide immediate remediation steps before external auditors arrive.
                """

                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.2
                )

                verdict = completion.choices[0].message.content
                st.error("Audit Gap Detected!") if "CRITICAL" in verdict or "HIGH" in verdict else st.success("Log Cleared")
                st.markdown(verdict)
