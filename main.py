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

    # 🤖 Agent 1: Scout (Stream Critical Flaws)
    scout_prompt = f"""You are a ruthless UX Auditor. Your goal is to identify revenue-killing friction points. 
Identify 3 critical issues. Do not be vague. 
Focus on: Conversion friction, trust signals, and user path clarity.

FORMAT:
### 🔍 [Name of Issue]
**IMPACT:** [Explain why this kills conversion in one sentence.]
**SIGNAL:** [Why this is a problem based on the URL provided.]"""
    scout_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": scout_prompt}, {"role": "user", "content": site_text}], stream=True)
    scout_report = ""
    for chunk in scout_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            scout_report += token
            yield f"data: {json.dumps({'scout_analysis': token})}\n\n"
    
    # 🤖 Agent 2: Builder (CFO-Grade Revenue Analysis)
    builder_sys = f"""You are a Chief Growth Officer. You don't offer suggestions; you offer financial solutions.
For each flaw found by the Scout, you MUST quantify the cost of doing nothing.

FORMAT (No tables):

### 🚨 FLAW: [Name]
**REVENUE LEAK:** $[Estimated amount]/mo (Estimate based on industry standard SaaS benchmarks).
**THE FIX:** [Concrete, specific technical/design step.]
**ROI FORECAST:** [How much revenue we recover by fixing this immediately.]

TONE: Professional, authoritative, CFO-level.
NO PLACEHOLDERS. If unsure, make a high-probability estimate based on industry standards.
Budget constraints: {pricing_rules}. NO introductions. Start with the first flaw."""
    builder_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": builder_sys}, {"role": "user", "content": scout_report}], stream=True)
    full_builder_report = ""
    for chunk in builder_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_builder_report += token
            yield f"data: {json.dumps({'builder_blueprint': token})}\n\n"

    # 🤖 Agent 3: Salesman (Short)
    salesman_sys = f"Draft a concise sales email (max 100 words) for {site_type}. Focus on ROI and pain point. Use short paragraphs. No fluff."
    salesman_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": salesman_sys}, {"role": "user", "content": full_builder_report}], stream=True)
    full_sales_pitch = ""
    for chunk in salesman_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_sales_pitch += token
            yield f"data: {json.dumps({'salesman_pitch': token})}\n\n"

    # 🤖 Agent 4: LinkedIn (Short)
    linkedin_sys = f"Draft a 2-sentence LinkedIn DM for {site_type}. Extremely conversational and direct. No greeting."
    linkedin_stream = client.chat.completions.create(model=FREE_BRAIN, messages=[{"role": "system", "content": linkedin_sys}, {"role": "user", "content": full_builder_report}], stream=True)
    full_linkedin_pitch = ""
    for chunk in linkedin_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_linkedin_pitch += token
            yield f"data: {json.dumps({'linkedin_pitch': token})}\n\n"

    save_to_db(target_url, scout_report, full_builder_report, full_sales_pitch, full_linkedin_pitch)
    yield "data: [DONE]\n\n"

@app.post("/analyze")
async def analyze_website_endpoint(request_data: AnalyzeRequest):
    return StreamingResponse(generate_crew_stream(request_data.url), media_type="text/event-stream")