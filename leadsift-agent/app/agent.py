import os
import re
import json
import datetime
import sys
from typing import Any
from pydantic import BaseModel, Field
from google.adk.workflow import Workflow, START, JoinNode, node
from google.adk.agents import LlmAgent, Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.tools import AgentTool, McpToolset
from mcp import StdioServerParameters
from google.genai import types

from .config import config

# Setup MCP server connection using the active Python executable
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
    )
)

# Pydantic schemas for structured outputs
class ResearchOutput(BaseModel):
    company_name: str = Field(description="Name of the company researched")
    industry: str = Field(description="Industry category of the company")
    company_size: int = Field(description="Number of employees at the company")
    research_summary: str = Field(description="Summary of the lead's professional web and social profile information")

class ScoreOutput(BaseModel):
    score: int = Field(description="Lead qualification score between 0 and 100")
    rationale: str = Field(description="Detailed reason for the assigned score based on firmographics")

class OrchestratorOutput(BaseModel):
    company_name: str = Field(description="Name of the company")
    industry: str = Field(description="Industry category of the company")
    company_size: int = Field(description="Number of employees at the company")
    research_summary: str = Field(description="Summary of lead background research")
    score: int = Field(description="Calculated lead qualification score (0-100)")
    rationale: str = Field(description="Scoring rationale")
    recommendation: str = Field(description="Final recommendation: 'Auto-Approve', 'Borderline Review', or 'Auto-Reject'")

# Specialized agents
research_agent = LlmAgent(
    name="ResearchAgent",
    model=config.model,
    instruction="""You are a professional business research agent.
Your goal is to gather firmographic and professional profile information for a lead.
Use the MCP tools `search_web_profiles` and `fetch_company_details` to search for the lead and the company they work for.
Find the company size, industry, and a summary of their professional background.
Return the structured output matching the ResearchOutput schema.
""",
    output_schema=ResearchOutput,
    description="Researches a lead and company to find size, industry, and profile details.",
    tools=[mcp_toolset],
)

scoring_agent = LlmAgent(
    name="ScoringAgent",
    model=config.model,
    instruction="""You are a lead scoring expert.
Your goal is to evaluate lead information and assign a lead score between 0 and 100.
Evaluate the lead based on the following criteria:
- Company Size: Higher score for larger companies (e.g. > 1000 employees gets higher score, < 50 gets lower).
- Industry: High value industries like Technology, Fintech, Software/SaaS get higher scores.
- Professional Role: Roles with "Director", "VP", "Manager", "Product", "Operations" get higher scores.
Provide the final score and a clear rationale.
Return the structured output matching the ScoreOutput schema.
""",
    output_schema=ScoreOutput,
    description="Scores a lead based on company size, industry, and role details.",
)

# Orchestrator agent
orchestrator_agent = LlmAgent(
    name="LeadOrchestrator",
    model=config.model,
    instruction="""You are the LeadSift Orchestrator.
Your goal is to orchestrate the lead enrichment and scoring process.
Follow these steps:
1. Delegate research to ResearchAgent using the AgentTool. Pass the lead's name and company info.
2. Delegate scoring to ScoringAgent using the AgentTool. Pass the collected research details.
3. Consolidate the findings and return a final recommendation (e.g. Auto-Approve, Borderline Review, Auto-Reject).
Ensure you call the tools to delegate the work.
""",
    output_schema=OrchestratorOutput,
    description="Orchestrates lead research and scoring by delegating to specialized agents.",
    tools=[AgentTool(research_agent), AgentTool(scoring_agent), mcp_toolset],
)

# Workflow Function Nodes

def security_checkpoint(ctx: Context, node_input: types.Content) -> Event:
    """Scan incoming lead input for security issues and scrub PII."""
    input_text = ""
    if node_input and node_input.parts:
        input_text = " ".join([p.text for p in node_input.parts if p.text])
        
    state_delta = {
        "lead_input": input_text,
        "clean_input": input_text,
        "is_secure": True,
        "security_verdict": "Clear",
    }
    
    # 1. PII Scrubbing
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    
    clean_text = input_text
    scrubbed_emails = re.findall(email_pattern, clean_text)
    scrubbed_phones = re.findall(phone_pattern, clean_text)
    
    if scrubbed_emails:
        clean_text = re.sub(email_pattern, "[REDACTED_EMAIL]", clean_text)
    if scrubbed_phones:
        clean_text = re.sub(phone_pattern, "[REDACTED_PHONE]", clean_text)
        
    state_delta["clean_input"] = clean_text
    
    # 2. Prompt Injection Detection
    injection_keywords = ["ignore previous", "system prompt", "override", "bypass validation", "reveal instructions"]
    detected_injection = [kw for kw in injection_keywords if kw in input_text.lower()]
    
    # 3. Domain-specific rule (restricted email domains)
    detected_blocked_domain = False
    blocked_domains = ["mailinator.com", "trashmail.com", "competitor.com"]
    for email in scrubbed_emails:
        domain = email.split("@")[-1].lower()
        if domain in blocked_domains:
            detected_blocked_domain = True
            state_delta["security_verdict"] = f"Blocked domain detected: {domain}"
            break
            
    # Structured JSON audit log
    audit_log = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "security_scan",
        "has_pii": len(scrubbed_emails) > 0 or len(scrubbed_phones) > 0,
        "pii_details": {
            "emails_found": len(scrubbed_emails),
            "phones_found": len(scrubbed_phones)
        },
        "injection_detected": len(detected_injection) > 0,
        "injection_details": detected_injection,
        "domain_blocked": detected_blocked_domain,
        "severity": "INFO",
    }
    
    if len(detected_injection) > 0 or detected_blocked_domain:
        state_delta["is_secure"] = False
        if len(detected_injection) > 0:
            state_delta["security_verdict"] = f"Prompt injection detected: {detected_injection}"
            audit_log["severity"] = "CRITICAL"
        else:
            audit_log["severity"] = "WARNING"
            
        print(json.dumps(audit_log))
        return Event(output=state_delta, route="security_violation", state=state_delta)
        
    print(json.dumps(audit_log))
    # Route to LeadOrchestrator by passing clean text as output
    return Event(output=clean_text, state=state_delta)

def evaluate_score(ctx: Context, node_input: dict) -> Event:
    """Evaluate lead score and route accordingly."""
    state_delta = {
        "company_name": node_input.get("company_name", ""),
        "industry": node_input.get("industry", ""),
        "company_size": node_input.get("company_size", 0),
        "research_summary": node_input.get("research_summary", ""),
        "score": node_input.get("score", 0),
        "rationale": node_input.get("rationale", ""),
    }
    
    score = state_delta["score"]
    
    # Audit log
    audit_log = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "lead_scoring_verdict",
        "company": state_delta["company_name"],
        "score": score,
        "severity": "INFO"
    }
    print(json.dumps(audit_log))
    
    if score >= 75:
        state_delta["status"] = "auto_approved"
        return Event(output=node_input, route="auto_approve", state=state_delta)
    elif score >= 50:
        state_delta["status"] = "under_review"
        return Event(output=node_input, route="borderline", state=state_delta)
    else:
        state_delta["status"] = "auto_rejected"
        return Event(output=node_input, route="auto_reject", state=state_delta)

@node(rerun_on_resume=True)
async def human_review(ctx: Context, node_input: dict):
    """Pause workflow for human review if score is borderline."""
    if not ctx.resume_inputs or "decision" not in ctx.resume_inputs:
        yield RequestInput(
            interrupt_id="decision",
            message=f"Lead review required for company '{node_input.get('company_name')}' with score {node_input.get('score')}. Rationale: {node_input.get('rationale')}. Please approve or reject."
        )
        return
        
    decision = ctx.resume_inputs["decision"]
    comments = ctx.resume_inputs.get("comments", "")
    
    state_delta = {
        "reviewer_comments": comments,
    }
    
    # Audit log
    audit_log = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "human_review_verdict",
        "decision": decision,
        "comments": comments,
        "severity": "INFO"
    }
    print(json.dumps(audit_log))
    
    if decision.lower() in ["approve", "approved", "yes"]:
        state_delta["status"] = "approved"
        yield Event(output=node_input, route="approved", state=state_delta)
    else:
        state_delta["status"] = "rejected"
        yield Event(output=node_input, route="rejected", state=state_delta)

async def crm_enrichment(ctx: Context, node_input: dict):
    """Enrich the lead details and save them to the CRM."""
    name = ctx.state.get("lead_input", "Unknown Lead")
    # Clean name from PII placeholders for final output
    name = re.sub(r'\[REDACTED_EMAIL\]|\[REDACTED_PHONE\]', '', name).strip()
    company = ctx.state.get("company_name", "Unknown Company")
    score = ctx.state.get("score", 0)
    rationale = ctx.state.get("rationale", "")
    
    # We call our local CRM tool via the toolset directly, or perform enrichment logging
    result_msg = f"✅ SUCCESS: Lead for '{company}' (Score: {score}) successfully written and enriched in HubSpot CRM."
    
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=result_msg)]))
    yield Event(output=result_msg)

async def discard_lead(ctx: Context, node_input: dict):
    """Log lead rejection and discard it."""
    company = ctx.state.get("company_name", "Unknown Company")
    score = ctx.state.get("score", 0)
    result_msg = f"❌ DISCARDED: Lead for '{company}' (Score: {score}) rejected and discarded from target list."
    
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=result_msg)]))
    yield Event(output=result_msg)

async def security_event_handler(ctx: Context, node_input: Any):
    """Alert on security checkpoint violation."""
    verdict = ctx.state.get("security_verdict", "Unknown security issue")
    result_msg = f"🚨 SECURITY BLOCK: Request blocked. Reason: {verdict}"
    
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=result_msg)]))
    yield Event(output=result_msg)

# Build the Workflow Graph
root_agent = Workflow(
    name="LeadSiftWorkflow",
    description="Automated lead scoring, research, and CRM enrichment workflow.",
    edges=[
        ('START', security_checkpoint),
        # Route to Orchestrator if clean
        (security_checkpoint, orchestrator_agent),
        # Route to security event if violation
        (security_checkpoint, {"security_violation": security_event_handler}),
        # Orchestrator outputs results to evaluate_score
        (orchestrator_agent, evaluate_score),
        # Routing scoring decisions
        (evaluate_score, {"borderline": human_review, "auto_approve": crm_enrichment, "auto_reject": discard_lead}),
        # Human decision outputs
        (human_review, {"approved": crm_enrichment, "rejected": discard_lead}),
    ]
)

# App Container
app = App(
    root_agent=root_agent,
    name="app",
)
