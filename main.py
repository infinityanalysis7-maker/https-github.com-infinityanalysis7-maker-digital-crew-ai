import os
import json
import psycopg2 
import urllib3
from datetime import datetime
import requests
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Application
load_dotenv()
app = FastAPI(title="Digital Crew AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
FREE_BRAIN = "openrouter/auto"

DATABASE_URL = os.getenv("DATABASE_URL")

def save_to_db(url, scout, builder, sales, linkedin):
    try:
        if not DATABASE_URL: return
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (url, scout_analysis, builder_blueprint, salesman_pitch, linkedin_pitch, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (url, scout, builder, sales, linkedin, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database save failed: {e}")

class AnalyzeRequest(BaseModel):
    url: str

def fetch_real_website_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=12, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]): script.extract()
            return soup.get_text(separator=' ')[:4000]
        return f"Error: Status code {response.status_code}"
    except Exception as e:
        return f"Connection failure: {str(e)}"

def classify_target_site(scraped_text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=FREE_BRAIN,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Classify: B2B_SAAS, E_COMMERCE, CONTENT_INFO, LOCAL_BUSINESS. Respond ONLY with JSON."},
                {"role": "user", "content": scraped_text[:3000]}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"site_type": "B2B_SAAS", "core_conversion_goal": "User subscriptions", "allowed_pricing_tier": "medium"}

def extract_final_output(full_text: str) -> str:
    """
    Extract clean FINAL OUTPUT section. 
    Fallback: if no marker found, return the whole text.
    """
    # Try ### FINAL OUTPUT first
    if "### FINAL OUTPUT" in full_text:
        parts = full_text.split("### FINAL OUTPUT", 1)
        result = parts[1].strip() if len(parts) > 1 else ""
        if result:  # Only return if non-empty
            return result
    
    # Try **FINAL OUTPUT:**
    if "**FINAL OUTPUT:**" in full_text:
        parts = full_text.split("**FINAL OUTPUT:**", 1)
        result = parts[1].strip() if len(parts) > 1 else ""
        if result:
            return result
    
    # Fallback: return everything, assume it's all output
    return full_text.strip()

async def generate_crew_stream(target_url: str):
    site_text = fetch_real_website_text(target_url)
    meta = classify_target_site(site_text)
    site_type = meta.get("site_type", "B2B_SAAS")
    goal = meta.get("core_conversion_goal", "conversion")
    pricing_tier = meta.get("allowed_pricing_tier", "medium")

    pricing_rules = {
        "low": "$1k-$4k",
        "medium": "$5k-$12k",
        "high": "$15k-$30k"
    }.get(pricing_tier, "$5k-$15k")

    # 🎯 USER CONTEXT (Customize this or inject from frontend)
    user_context = """
User Identity: I am a SaaS Agency Owner specializing in AI Automation.
My Service: We build custom AI chatbots that reduce customer support costs by 40%.
Target Audience: We sell to E-commerce brands with $1M+ ARR.
"""

    # 🤖 Agent 1: Scout (Aggressive Auditor - Master 10/10)
    scout_prompt = f"""You are a top-tier Growth Auditor. Your work is read by C-level executives.
- DO NOT use passive, soft language (e.g., 'potential,' 'could,' 'might'). 
- Use active, direct language (e.g., 'is bleeding,' 'costs,' 'prevents,' 'kills').
- Focus on the #1 conversion blocker on the page.
- FORMAT:
🔍 [NAME OF FLAW]
IMPACT: [One sentence showing the revenue damage].
SIGNAL: [One sentence explaining exactly where/how the site fails]."""
    
    scout_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": scout_prompt}, {"role": "user", "content": site_text}], stream=True)
    full_scout_raw = ""
    for chunk in scout_stream:
        token = chunk.choices[0].delta.content or ""
        full_scout_raw += token
    
    # Extract clean output after full collection
    scout_report = extract_final_output(full_scout_raw)
    
    # Stream the clean output to frontend
    yield f"data: {json.dumps({'scout_analysis': scout_report})}\n\n"

    # 🤖 Agent 2: Builder (CFO Strategist - Master 10/10)
    builder_sys = f"""You are a Chief Growth Officer modeling a turnaround strategy.
- Quantify the Revenue Leak with specific dollar amounts ($).
- THE FIX: Must be technical and specific (e.g., 'A/B test X,' 'Add Y button').
- ROI FORECAST: Project the recovery amount.
- FOR EACH FLAW, PROVIDE:
  ### 🚨 FLAW: [Name]
  **REVENUE LEAK:** $[amount]/mo
  **THE FIX:** [specific technical step]
  **ROI FORECAST:** $[recovery amount]/mo
- MANDATORY DISCLAIMER: At the very end of your response, add:
  'Note: Estimates are based on industry-standard SaaS benchmarks for strategic modeling purposes. Specific impact varies by site traffic.'
Budget constraints: {pricing_rules}. NO introductions. Start with the first flaw."""
    
    builder_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": builder_sys}, {"role": "user", "content": scout_report}], stream=True)
    full_builder_raw = ""
    for chunk in builder_stream:
        token = chunk.choices[0].delta.content or ""
        full_builder_raw += token
    
    # Extract clean output after full collection
    full_builder_report = extract_final_output(full_builder_raw)
    
    # Stream the clean output to frontend
    yield f"data: {json.dumps({'builder_blueprint': full_builder_report})}\n\n"

    # 🤖 Agent 3: Salesman (Collect full response, then stream clean output)
    salesman_sys = f"""You are a Senior B2B SaaS Closer. Write a 5-line outreach email.
- NO PLACEHOLDERS like [Pain Point]. 
- Infer the pain from the Builder's analysis and inject it into the email.
- Tone: Direct, punchy, value-first.
- NO FLUFF.

**USER CONTEXT (Personalize your pitch to this identity):**
User Identity: I am a SaaS ASynthesizer - Master 10/10 with Mandatory Mapping)
    salesman_sys = f"""You are a Senior SaaS Closer. Your email MUST map directly to the audit data.
- MANDATORY MAPPING:
    1. Reference the Exact Flaw Name from the Builder (do not paraphrase).
    2. Reference the Exact Revenue Leak ($) from the Builder (must include the dollar amount).
- STRUCTURE:
    LINE 1: The 'Pattern Interrupt' (Name the flaw and the $ amount lost).
    LINE 2: The 'Problem' (Why it hurts their growth).
    LINE 3: The 'Solution' (Your AI Agency's 40% cost reduction).
    LINE 4: The 'CTA' (A low-friction next step).
- NO GENERIC FLUFF. If you do not include the exact numbers and flaw names provided by the Builder, you are failing your job.
- USER CONTEXT: You are a SaaS Agency Owner specializing in AI Automation. You build custom AI chatbots that reduce customer support costs by 40%. You sell to E-commerce brands with $1M+ ARR.ean output after full collection
    full_sales_pitch = extract_final_output(full_sales_raw)
    
    # Stream the clean output to frontend
    yield f"data: {json.dumps({'salesman_pitch': full_sales_pitch})}\n\n"

    # 🤖 Agent 4: Reviewer (Validation Only, Non-blocking)
    reviewer_sys = f"""You are the Quality Control Director. Review the Builder's audit and the Salesman's email.
CHECKLIST:
1. Did the Salesman reference the SPECIFIC flaw the Builder found? (No generic language allowed)
2. Is the email tone actually aligned with the User Identity provided?
3. Is the ROI calculation plausible and backed by the Builder's analysis?

If ALL pass, output: "✅ ALIGNMENT VERIFIED"
If ANY fail, output: "⚠️ MISGatekeeper - Master 10/10 with Rewrite Authority)
    reviewer_sys = f"""You are the Quality Control Director. You hold the Salesman to a strict standard.
VERIFY THESE 3 THINGS:
1. Did the Salesman include the exact Flaw Name identified by the Builder? (Yes/No)
2. Did the Salesman include the exact Dollar Amount ($) calculated by the Builder? (Yes/No)
3. Is the tone direct and professional? (Yes/No)

IF ALL ARE YES: Output the Salesman email exactly as is.
IF ANY ARE NO: Rewrite the email yourself, ensuring all data is perfectly synthesized. Make sure to include the exact flaw name and exact dollar amount from the Builder
Use the Builder's findings to inform the tone and message.

**INTERNAL THOUGHT STEP:**
ANALYZE: What's the hook from the Builder's findings?
REFINE: Make it personal, not templated.

**FINAL OUTPUT:**"""
    
    linkedin_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": linkedin_sys}, {"role": "user", "content": full_builder_report}], stream=True)
    full_linkedin_raw = ""
    for chunk in linkedin_stream:
        token = chunk.choices[0].delta.content or ""
        full_linkedin_raw += token
    
    # Extract clean output after full collection
    full_linkedin_pitch = extract_final_output(full_linkedin_raw)
    
    # Stream the clean output to frontend
    yield f"data: {json.dumps({'linkedin_pitch': full_linkedin_pitch})}\n\n"

    # Save to database
    save_to_db(target_url, scout_report, full_builder_report, full_sales_pitch, full_linkedin_pitch)
    
    # Send final consolidated payload
    yield f"data: {json.dumps({'scout_analysis': scout_report, 'builder_blueprint': full_builder_report, 'salesman_pitch': full_sales_pitch, 'linkedin_pitch': full_linkedin_pitch, 'review_status': review_status})}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/analyze")
async def analyze_website_endpoint(request_data: AnalyzeRequest):
    return StreamingResponse(generate_crew_stream(request_data.url), media_type="text/event-stream")