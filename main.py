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
    """Extract clean FINAL OUTPUT section, stripping the marker itself."""
    if "### FINAL OUTPUT" in full_text:
        # Split on ### FINAL OUTPUT and take everything after it
        parts = full_text.split("### FINAL OUTPUT", 1)
        if len(parts) > 1:
            return parts[1].strip()
    if "**FINAL OUTPUT:**" in full_text:
        # Handle bold version
        parts = full_text.split("**FINAL OUTPUT:**", 1)
        if len(parts) > 1:
            return parts[1].strip()
    return full_text

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

    # 🤖 Agent 1: Scout (With Chain of Thought - Clean Stream)
    scout_prompt = f"""You are a ruthless UX Auditor. Your goal is to identify revenue-killing friction points. 
Identify 3 critical issues. Do not be vague. 
Focus on: Conversion friction, trust signals, and user path clarity.

**INTERNAL THOUGHT STEP (HIDE THIS IN FINAL OUTPUT):**
ANALYZE: Break down the data to find friction points.
CRITIQUE: List 2 reasons why your initial interpretation might be wrong.
REFINE: Correct your analysis based on critique.

**THEN PROVIDE FINAL OUTPUT BELOW:**

### FINAL OUTPUT

### 🔍 [Name of Issue]
**IMPACT:** [Explain why this kills conversion in one sentence.]
**SIGNAL:** [Why this is a problem based on the URL provided.]"""
    
    scout_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": scout_prompt}, {"role": "user", "content": site_text}], stream=True)
    full_scout_raw = ""
    scout_report = ""
    found_final_output = False
    
    for chunk in scout_stream:
        token = chunk.choices[0].delta.content or ""
        full_scout_raw += token
        
        if "### FINAL OUTPUT" in full_scout_raw and not found_final_output:
            found_final_output = True
            # Extract everything after the marker
            scout_report = full_scout_raw.split("### FINAL OUTPUT", 1)[1].strip()
            # Stream the clean portion (without the marker)
            yield f"data: {json.dumps({'scout_analysis': scout_report})}\n\n"
        elif found_final_output:
            # Continue accumulating and streaming
            scout_report = full_scout_raw.split("### FINAL OUTPUT", 1)[1].strip()
            # Stream only the new token
            yield f"data: {json.dumps({'scout_analysis': token})}\n\n"
    
    # Final clean scout_report for downstream use
    scout_report = extract_final_output(full_scout_raw)

    # 🤖 Agent 2: Builder (CFO-Grade, With Chain of Thought - Clean Stream)
    builder_sys = f"""You are a Chief Growth Officer. You don't offer suggestions; you offer financial solutions.
For each flaw found by the Scout, you MUST quantify the cost of doing nothing.

**INTERNAL THOUGHT STEP (HIDE THIS IN FINAL OUTPUT):**
ANALYZE: Break down each flaw and estimate revenue impact.
CRITIQUE: Are these estimates too conservative or too aggressive? What assumptions am I making?
REFINE: Adjust estimates based on industry benchmarks and logic.

**THEN PROVIDE FINAL OUTPUT BELOW:**

### FINAL OUTPUT

### 🚨 FLAW: [Name]
**REVENUE LEAK:** $[Estimated amount]/mo (Estimate based on industry standard SaaS benchmarks).
**THE FIX:** [Concrete, specific technical/design step.]
**ROI FORECAST:** [How much revenue we recover by fixing this immediately.]

TONE: Professional, authoritative, CFO-level.
NO PLACEHOLDERS. If unsure, make a high-probability estimate based on industry standards.
Budget constraints: {pricing_rules}. NO introductions. Start with the first flaw."""
    
    builder_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": builder_sys}, {"role": "user", "content": scout_report}], stream=True)
    full_builder_raw = ""
    full_builder_report = ""
    found_final_output = False
    
    for chunk in builder_stream:
        token = chunk.choices[0].delta.content or ""
        full_builder_raw += token
        
        if "### FINAL OUTPUT" in full_builder_raw and not found_final_output:
            found_final_output = True
            full_builder_report = full_builder_raw.split("### FINAL OUTPUT", 1)[1].strip()
            yield f"data: {json.dumps({'builder_blueprint': full_builder_report})}\n\n"
        elif found_final_output:
            full_builder_report = full_builder_raw.split("### FINAL OUTPUT", 1)[1].strip()
            yield f"data: {json.dumps({'builder_blueprint': token})}\n\n"
    
    full_builder_report = extract_final_output(full_builder_raw)

    # 🤖 Agent 3: Salesman (With Chain of Thought & User Context - Clean Stream)
    salesman_sys = f"""You are a Senior B2B SaaS Closer. Write a 5-line outreach email.
- NO PLACEHOLDERS like [Pain Point]. 
- Infer the pain from the Builder's analysis and inject it into the email.
- Tone: Direct, punchy, value-first.
- NO FLUFF.

**USER CONTEXT (Personalize your pitch to this identity):**
{user_context}

**INTERNAL THOUGHT STEP (HIDE THIS IN FINAL OUTPUT):**
ANALYZE: What are the specific flaws and revenue leaks the Builder found?
CRITIQUE: How does OUR service (AI chatbots for support cost reduction) directly solve these?
REFINE: Craft an email that explicitly connects the flaw to our solution.

**THEN PROVIDE FINAL OUTPUT BELOW:**

### FINAL OUTPUT"""
    
    salesman_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": salesman_sys}, {"role": "user", "content": full_builder_report}], stream=True)
    full_sales_raw = ""
    full_sales_pitch = ""
    found_final_output = False
    
    for chunk in salesman_stream:
        token = chunk.choices[0].delta.content or ""
        full_sales_raw += token
        
        if "### FINAL OUTPUT" in full_sales_raw and not found_final_output:
            found_final_output = True
            full_sales_pitch = full_sales_raw.split("### FINAL OUTPUT", 1)[1].strip()
            yield f"data: {json.dumps({'salesman_pitch': full_sales_pitch})}\n\n"
        elif found_final_output:
            full_sales_pitch = full_sales_raw.split("### FINAL OUTPUT", 1)[1].strip()
            yield f"data: {json.dumps({'salesman_pitch': token})}\n\n"
    
    full_sales_pitch = extract_final_output(full_sales_raw)

    # 🤖 Agent 4: Reviewer (Quality Control - Validation Only, No Stream Overwrite)
    reviewer_sys = f"""You are the Quality Control Director. Review the Builder's audit and the Salesman's email.
CHECKLIST:
1. Did the Salesman reference the SPECIFIC flaw the Builder found? (No generic language allowed)
2. Is the email tone actually aligned with the User Identity provided?
3. Is the ROI calculation plausible and backed by the Builder's analysis?

If ALL pass, output: "✅ ALIGNMENT VERIFIED"
If ANY fail, output: "⚠️ MISALIGNMENT DETECTED - CORRECTIONS NEEDED"

User Identity for context:
{user_context}"""
    
    reviewer_input = f"BUILDER AUDIT:\n{full_builder_report}\n\nSALESMAN EMAIL:\n{full_sales_pitch}"
    reviewer_response = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": reviewer_sys}, {"role": "user", "content": reviewer_input}])
    review_status = reviewer_response.choices[0].message.content
    yield f"data: {json.dumps({'review_status': review_status})}\n\n"

    # 🤖 Agent 5: LinkedIn (With Chain of Thought - Clean Stream)
    linkedin_sys = f"""Draft a 2-sentence LinkedIn DM for {site_type}. Extremely conversational and direct. No greeting.
Use the Builder's findings to inform the tone and message.

**INTERNAL THOUGHT STEP:**
ANALYZE: What's the hook from the Builder's findings?
REFINE: Make it personal, not templated.

**FINAL OUTPUT:**"""
    
    linkedin_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": linkedin_sys}, {"role": "user", "content": full_builder_report}], stream=True)
    full_linkedin_raw = ""
    full_linkedin_pitch = ""
    found_final_output = False
    
    for chunk in linkedin_stream:
        token = chunk.choices[0].delta.content or ""
        full_linkedin_raw += token
        
        if "**FINAL OUTPUT:**" in full_linkedin_raw and not found_final_output:
            found_final_output = True
            full_linkedin_pitch = full_linkedin_raw.split("**FINAL OUTPUT:**", 1)[1].strip()
            yield f"data: {json.dumps({'linkedin_pitch': full_linkedin_pitch})}\n\n"
        elif found_final_output:
            full_linkedin_pitch = full_linkedin_raw.split("**FINAL OUTPUT:**", 1)[1].strip()
            yield f"data: {json.dumps({'linkedin_pitch': token})}\n\n"
    
    full_linkedin_pitch = extract_final_output(full_linkedin_raw)

    # Save to database
    save_to_db(target_url, scout_report, full_builder_report, full_sales_pitch, full_linkedin_pitch)
    
    # Send final consolidated payload with strict keys
    yield f"data: {json.dumps({'scout_analysis': scout_report, 'builder_blueprint': full_builder_report, 'salesman_pitch': full_sales_pitch, 'linkedin_pitch': full_linkedin_pitch})}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/analyze")
async def analyze_website_endpoint(request_data: AnalyzeRequest):
    return StreamingResponse(generate_crew_stream(request_data.url), media_type="text/event-stream")