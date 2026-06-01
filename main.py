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

# 2. Load Secret Keys & Database Path
load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
FREE_BRAIN = "openrouter/auto"

# FIX: Render requires writing to /tmp for persistent file operations
# --- DATABASE PATH FIX FOR RENDER ---
# This ensures it writes to /tmp, which is the only place Render allows!
if os.environ.get("RENDER"):
    DB_FILE = "/tmp/leads.db"
else:
    DB_FILE = "leads.db"

d# --- DATABASE PATH FIX FOR RENDER ---
# This ensures it writes to /tmp, which is the only place Render allows!
# --- DATABASE PATH FIX FOR RENDER ---
# If running on Render, use /tmp. Otherwise, use local file.
import os

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

# Initialize
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

# 🛠️ STEP 1 ADDITION: Site Classifier Function
def classify_target_site(scraped_text: str) -> dict:
    """
    Analyzes raw scraped text to determine the business framework,
    preventing generic boilerplate SaaS pitches on non-SaaS sites.
    """
    print("🧠 Running Luminous Classification Protocol...")
    try:
        response = client.chat.completions.create(
            model=FREE_BRAIN,
            response_format={"type": "json_object"}, # Force clean JSON compilation
            messages=[
                {"role": "system", "content": """You are an elite business model auditor. 
                Analyze the scraped text snippet from a website and classify it into one of these exact categories:
                - B2B_SAAS (Software platforms, utility tools, tech infrastructure)
                - E_COMMERCE (Online retail storefronts, physical goods marketplace)
                - CONTENT_INFO (Blogs, educational portals, forums, news aggregators, reference materials)
                - LOCAL_BUSINESS (Agencies, service providers, brick-and-mortar storefronts)
                
                Respond ONLY with a valid JSON object matching this structure:
                {
                    "site_type": "ONE_OF_THE_ABOVE",
                    "core_conversion_goal": "What metric does this specific site type care about optimizing most? (e.g., Lead capturing, content retention, subscription signups, cart checkouts)",
                    "allowed_pricing_tier": "low" (for content/blogs/local) or "medium" (for medium projects) or "high" (for complex enterprise SaaS/Ecomm platforms)
                }"""},
                {"role": "user", "content": scraped_text[:3000]}
            ]
        )
        
        # Safe JSON parse execution
        data = json.loads(response.choices[0].message.content)
        print(f"📊 Site Categorized Successfully: {data.get('site_type')}")
        return data
    except Exception as e:
        print(f"⚠️ Classification error, defaulting: {str(e)}")
        return {
            "site_type": "B2B_SAAS",
            "core_conversion_goal": "User subscriptions and pipeline conversions",
            "allowed_pricing_tier": "medium"
        }

# --- STREAMING GENERATOR ENGINE (CONTEXT-AWARE EDITION) ---
async def generate_crew_stream(target_url: str):
    print(f"📡 Starting Streaming Pipeline for: {target_url}")
    
    site_text = fetch_real_website_text(target_url)
    
    # Run our brand new background classifier
    meta = classify_target_site(site_text)
    site_type = meta.get("site_type", "B2B_SAAS")
    goal = meta.get("core_conversion_goal", "system optimization")
    pricing_tier = meta.get("allowed_pricing_tier", "medium")

    # Dynamic pricing constraint rulebook configuration passed to the system prompt
    pricing_rules = {
        "low": "Keep pricing strictly realistic. Small optimizations must fall inside a modest $1,500 - $4,500 spectrum. Never pitch massive high tier enterprise costs.",
        "medium": "Standard structural overhauls should land within an analytical $5,000 - $12,000 baseline budget.",
        "high": "Complex enterprise integrations or high-scale multi-funnel architectures can expand safely into premium $15,000 - $30,000+ budgets."
    }.get(pricing_tier, "Keep budget allocations inside a $5,000 - $15,000 range.")

    # 🤖 Agent 1: Scout (Short, Context-Aware Diagnostics)
    scout_res = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[
            {"role": "system", "content": f"""You are an elite cyber auditor evaluating a platform categorized as: {site_type}.
            Your core analytical objective is finding flaws linked explicitly to: {goal}.
            
            Analyze the text and list exactly 3 distinct, authentic technical or structural structural flaws. 
            Do not guess or assume. If the site is simple or static, do not invent heavy server bugs; focus on layout clarity, asset speed, structural metadata, or navigation gaps.
            Never write paragraphs or multi-sentence explanations. 
            
            Format exactly like this example template structure using clean markdown lists:
            ⚠️ PERFORMANCE LEAK: [Short direct finding specific to the content] (Impact: Loss of {goal})
            🛑 UI/UX FRICTION: [Short direct finding specific to the layout] (Impact: Negative User Experience)
            🔧 ARCHITECTURE GAP: [Short direct finding specific to the system stack] (Impact: Long-term Risk)"""},
            {"role": "user", "content": site_text}
        ]
    )
    scout_report = scout_res.choices[0].message.content
    
    # 🤖 Agent 2: Builder (Clean Upgrade Protocols + Cost Data Grid)
    builder_stream = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[
            {"role": "system", "content": f"""You are a master systems architect building a technical fix matrix for a {site_type} portal.
            Convert the incoming audit report flaws into a crisp, hyper-structured 'Upgrade Protocol' tailored directly to resolving concerns about: {goal}.
            
            PRICING CONSTRAINT RULEBOARD: {pricing_rules}
            
            Do not use generic paragraphs or markdown bold symbols (***). Use clean single headers and lists.
            Ensure you include a detailed 'Commercial Quote' break-out structure at the end containing a calculated 'Total Upgrade Cost' row based on your rules.
            
            Format exactly like this example structure layout:
            ### ⚡ UPGRADE PROTOCOL
            * [Actionable Blueprint Fix 1] | [Direct performance value metric]
            * [Actionable Blueprint Fix 2] | [Direct operational reliability metric]
            * [Actionable Blueprint Fix 3] | [Direct value-add impact adjustment]
            
            ### 💰 COMMERCIAL QUOTE
            * Base Integration Module: $X,XXX
            * Engineering Layout Labor: $X,XXX
            * Total Upgrade Cost: $X,XXX
            * Expected ROI Target: Optimization of {goal}"""},
            {"role": "user", "content": scout_report}
        ],
        stream=True
    )
    
    full_builder_report = ""
    for chunk in builder_stream:
        token = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
        if token:
            full_builder_report += token
            yield f"data: {json.dumps({'builder_blueprint': token})}\n\n"

    # 🤖 Agent 3: Salesman (Contextual & Consultative Pitch Deck Engine)
    salesman_stream = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[
            {"role": "system", "content": f"""You are a precision technical account executive closing deals in the {site_type} space. 
            Draft a hyper-short, consultative outbound technical sales email pitching the exact upgrades and financial values calculated inside the blueprint.
            
            CRITICAL ANTI-BOILERPLATE SAFEGUARDS:
            - Never use generic high-pressure fear phrases like 'your platform is dropping user trust' or 'severe server crashes' unless the blueprint explicitly documents it.
            - Match the tone to the industry. Content platforms want smooth performance; businesses want revenue.
            - Directly insert the accurate numbers and costs from the blueprint text into your placeholders.
            
            Format exactly like this example template:
            **SUBJECT: Technical Implementation Strategy for Target Platform**
            
            Dear [Contact Name],
            
            We completed a systems analysis of your digital presence and engineered an deployment roadmap targeting key optimizations across your {site_type} infrastructure:
            
            📦 THE BLUEPRINT:
            • [Extract Core Protocol Fix 1 From Blueprint]
            • [Extract Core Protocol Fix 2 From Blueprint]
            • Total Projected Effort: [Insert EXACT Total Upgrade Cost from the Builder Quote]
            
            📈 PERFORMANCE UPLIFT:
            Our engineering blueprints focus on driving a direct improvement to your target baseline: {goal}.
            
            Are you open to a brief 10-minute technical brief this week to review the structural architecture map?
            
            Best,
            [Your Name]"""},
            {"role": "user", "content": full_builder_report}
        ],
        stream=True
    )
    
    full_sales_pitch = ""
    for chunk in salesman_stream:
        token = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
        if token:
            full_sales_pitch += token
            yield f"data: {json.dumps({'salesman_pitch': token})}\n\n"

    # 🤖 Agent 4: LinkedIn Closer (Short, Dynamic DM Pattern-Breaker)
    linkedin_stream = client.chat.completions.create(
        model=FREE_BRAIN,
        messages=[
            {"role": "system", "content": f"""You are an elite, network-relationship architect reaching out to a company running a {site_type} site. 
            Draft a pattern-breaking LinkedIn message (strictly under 100 words). 
            Completely avoid corporate baseline assumptions, sales jargon, emojis, or superficial introductory fluff. Focus directly on optimizing: {goal}.
            
            Format exactly like this layout:
            **HEADS UP, [CONTACT_NAME]**
            
            Ran a engineering diagnostic cross check over your digital platform. We mapped out an implementation path focused directly on addressing your platform's operational bottlenecks and accelerating your {goal} baseline.
            
            🔥 AUDIT PROFILE SCORE:
            • Severity Rating: [Assign a realistic score out of 10 based on blueprint context]
            • Target Focus: Optimization of {goal}
            • Deployment Blueprint: Configured
            
            Would you be open to a quick 5-minute technical review deck detailing these architecture points?"""},
            {"role": "user", "content": full_builder_report}
        ],
        stream=True
    )
    
    full_linkedin_pitch = ""
    for chunk in linkedin_stream:
        token = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
        if token:
            full_linkedin_pitch += token
            yield f"data: {json.dumps({'linkedin_pitch': token})}\n\n"

    # Save to DB
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (url, scout_analysis, builder_blueprint, salesman_pitch, linkedin_pitch, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (target_url, scout_report, full_builder_report, full_sales_pitch, full_linkedin_pitch, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        print(f"💾 Saved complete run for {target_url} to leads.db!")
    except Exception as e:
        print(f"⚠️ Database save failed: {str(e)}")

    yield "data: [DONE]\n\n"

# --- THE RECEIVER PORT ---
@app.post("/analyze")
async def analyze_website_endpoint(request_data: AnalyzeRequest):
    if not request_data.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    return StreamingResponse(generate_crew_stream(request_data.url), media_type="text/event-stream")