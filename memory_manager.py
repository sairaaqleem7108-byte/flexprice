import os
import json
import asyncio
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_KEY = os.getenv("HINDSIGHT_API_KEY")
BANK_ID = "soc2-compliance-bank"

def _run_async(coro):
    """Executes async coroutine safely in new event loop thread or loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

def seed_hindsight_memory():
    """Populates Hindsight memory bank with past audit history and controls."""
    if not os.path.exists("seed_data.json"):
        return "seed_data.json not found!"

    with open("seed_data.json", "r") as f:
        data = json.load(f)

    async def _seed():
        client = Hindsight(
            base_url="https://api.hindsight.vectorize.io",
            api_key=HINDSIGHT_KEY
        )
        try:
            for finding in data.get("past_audit_findings", []):
                text = f"Audit Finding {finding['finding_id']} ({finding['year']}): Control {finding['control_id']} failed. Details: {finding['description']}. Severity: {finding['severity']}"
                await client.aretain(bank_id=BANK_ID, content=text, context="past_audit_finding")

            for ctrl in data.get("tested_controls", []):
                text = f"Control {ctrl['control_id']} ({ctrl['control_name']}): Tested frequency is {ctrl['frequency']}. Last tested on {ctrl['last_tested_date']}. Status: {ctrl['status']}"
                await client.aretain(bank_id=BANK_ID, content=text, context="control_schedule")
        finally:
            await client.aclose()

    _run_async(_seed())
    return "Hindsight Memory Seeded Successfully!"

def recall_audit_context(query: str):
    """Queries Hindsight memory to find related audit history or controls."""
    async def _recall():
        client = Hindsight(
            base_url="https://api.hindsight.vectorize.io",
            api_key=HINDSIGHT_KEY
        )
        try:
            response = await client.arecall(bank_id=BANK_ID, query=query)
            memories = [r.text for r in response.results]
            return "\n".join(memories) if memories else "No prior audit memory found."
        finally:
            await client.aclose()

    return _run_async(_recall())

def get_all_past_audit_findings():
    """Retrieves and parses all past audit findings stored in Hindsight memory."""
    import re

    async def _list():
        client = Hindsight(
            base_url="https://api.hindsight.vectorize.io",
            api_key=HINDSIGHT_KEY
        )
        try:
            response = await client.alist_memories(bank_id=BANK_ID)
            return getattr(response, "items", [])
        finally:
            await client.aclose()

    try:
        items = _run_async(_list())
    except Exception as e:
        print("Error in get_all_past_audit_findings:", e)
        return []

    findings_items = [item for item in items if getattr(item, "context", None) == "past_audit_finding"]
    if not findings_items:
        findings_items = [item for item in items if "audit finding" in getattr(item, "text", "").lower()]

    findings = []
    seen_ids = set()

    for item in findings_items:
        text = item.text
        fnd_match = re.search(r"FND-\d+-\d+", text)
        finding_id = fnd_match.group(0) if fnd_match else None

        if finding_id and finding_id in seen_ids:
            continue
        if finding_id:
            seen_ids.add(finding_id)

        ctrl_match = re.search(r"CC\d+\.\d+", text)
        sev_match = re.search(r"Severity:\s*(\w+)|(High|Medium|Low|Critical)\s+(?:severity|audit finding)", text, re.IGNORECASE)

        if sev_match:
            severity = (sev_match.group(1) or sev_match.group(2)).capitalize()
        else:
            severity = "N/A"

        findings.append({
            "Finding ID": finding_id or "N/A",
            "Control ID": ctrl_match.group(0) if ctrl_match else "N/A",
            "Severity": severity,
            "Details": text
        })

    return findings
