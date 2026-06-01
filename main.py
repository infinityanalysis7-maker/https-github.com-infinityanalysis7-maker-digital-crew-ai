import os
import sqlite3
import json
from datetime import datetime
import requests
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 1. Initialize the FastAPI Web Port
app = FastAPI(title="Digital Crew AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Load Secret Keys
load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
FREE_BRAIN = "openrouter/auto"

# 3. Database Path (Fixed for Render & Local)
# Only defined ONCE here to prevent conflicts.
if os.environ.get("RENDER"):
    DB_FILE = "/tmp/leads.db"
else:
    DB_FILE = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            scout_analysis TEXT,
            builder_blueprint TEXT,
            salesman_pitch TEXT,
            linkedin_pitch TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {DB_FILE}")

# Initialize Database
init_db()

class AnalyzeRequest(BaseModel):
    url: str

def fetch_real_website_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=12, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
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
                {"role": "system", "content": """You are an elite business model auditor. 
                Classify: B2B_SAAS, E_COMMERCE, CONTENT_INFO, LOCAL_BUSINESS.
                Respond ONLY with JSON: {"site_type": "...", "core_conversion_goal": "...", "allowed_pricing_tier": "..."}"""},
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
    goal = meta.get("core_conversion_goal", "system optimization")
    pricing_tier = meta.get("allowed_pricing_tier", "medium")

    pricing_rules = {
        "low": "Keep pricing strictly realistic. $1,500 - $4,500 range.",
        "medium": "Standard structural overhauls, $5,000 - $12,000 range.",
        "high": "Complex enterprise integrations, $15,000 - $30,000+ range."
    }.get(pricing_tier, "Keep budget allocations inside a $5,000 - $15,000 range.")

    # 🤖 Agent 1: Scout
    scout_res = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[{"role": "system", "content": f"You are a cyber auditor for {site_type}. Find 3 flaws targeting {goal}. Format: Markdown list."}, {"role": "user", "content": site_text}]
    )
    scout_report = scout_res.choices[0].message.content
    
    # 🤖 Agent 2: Builder
    builder_stream = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[{"role": "system", "content": f"Build a fix matrix for {site_type}. Budget: {pricing_rules}. Include Commercial Quote section."}, {"role": "user", "content": scout_report}],
        stream=True
    )
    full_builder_report = ""
    for chunk in builder_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_builder_report += token
            yield f"data: {json.dumps({'builder_blueprint': token})}\n\n"

    # 🤖 Agent 3: Salesman
    salesman_stream = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[{"role": "system", "content": f"Draft a consultative sales email for {site_type}. Target: {goal}."}, {"role": "user", "content": full_builder_report}],
        stream=True
    )
    full_sales_pitch = ""
    for chunk in salesman_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_sales_pitch += token
            yield f"data: {json.dumps({'salesman_pitch': token})}\n\n"

    # 🤖 Agent 4: LinkedIn
    linkedin_stream = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[{"role": "system", "content": f"Draft a LinkedIn DM for {site_type}. Target: {goal}."}, {"role": "user", "content": full_builder_report}],
        stream=True
    )
    full_linkedin_pitch = ""
    for chunk in linkedin_stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_linkedin_pitch += token
            yield f"data: {json.dumps({'linkedin_pitch': token})}\n\n"

    # Save to DB
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO scans (url, scout_analysis, builder_blueprint, salesman_pitch, linkedin_pitch, timestamp) VALUES (?, ?, ?, ?, ?, ?)''', 
                       (target_url, scout_report, full_builder_report, full_sales_pitch, full_linkedin_pitch, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database save failed: {e}")

    yield "data: [DONE]\n\n"

@app.post("/analyze")
async def analyze_website_endpoint(request_data: AnalyzeRequest):
    if not request_data.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    return StreamingResponse(generate_crew_stream(request_data.url), media_type="text/event-stream")