# ============================================
#  CELL 1 — INSTALL & IMPORT
# ============================================
!pip install -q python-pptx reportlab nest-asyncio openpyxl

import os
from kaggle_secrets import UserSecretsClient
import asyncio
import nest_asyncio
nest_asyncio.apply()

GOOGLE_API_KEY = UserSecretsClient().get_secret("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

from google.adk.agents import LlmAgent
from google.adk.tools.google_search_tool import google_search
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

import json
import re
import pandas as pd
import uuid
from pptx import Presentation
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

print("✅ Setup complete")

# ============================================
#  CELL 2 — CONFIGURE TRIP
# ============================================
ORIGIN = "Bangalore"
DESTINATION = "Bangkok"
START_DATE = "2025-12-10"
END_DATE = "2025-12-15"
TRAVELERS = 2
PREFERENCES = "temples, markets, river cruise"

print(f"""
Trip Configuration:
  {ORIGIN} → {DESTINATION}
  {START_DATE} to {END_DATE}
  {TRAVELERS} travelers
  Interests: {PREFERENCES}
""")

# ============================================
#  CELL 3 — CREATE & RUN AGENT
# ============================================
agent = LlmAgent(
    name="TravelPlanner",
    model=Gemini(
        model="gemini-2.0-flash-exp",
        generation_config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=8000,
            response_mime_type="application/json"
        )
    ),
    instruction="""You are a travel planner. Use google_search to find real information.
    
Output ONLY valid JSON:
{
  "flights": [{"airline": "X", "price": "$Y", "duration": "Zh"}],
  "hotels": [{"name": "X", "price": "$Y", "rating": "Z"}],
  "attractions": [{"name": "X", "cost": "$Y"}],
  "daily_plan": [{"day": 1, "activities": ["X", "Y"]}]
}""",
    tools=[google_search]
)

runner = InMemoryRunner(agent=agent)

prompt = f"""Plan a trip from {ORIGIN} to {DESTINATION}, {START_DATE} to {END_DATE}, {TRAVELERS} people.
Search for: flights, hotels, {PREFERENCES}.
Return JSON itinerary."""

print("Running agent...")

async def get_itinerary():
    return await runner.run_debug(user_messages=prompt, quiet=True)

result = asyncio.run(get_itinerary())
print(f"✅ Got {len(result)} events")

# ============================================
#  CELL 4 — EXTRACT & CLEAN TEXT
# ============================================
text = ""
for event in result:
    if hasattr(event, 'content') and event.content:
        if hasattr(event.content, 'parts') and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text'):
                    text += part.text

# Clean up markdown code fences if present
if text.strip().startswith('```'):
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)
    print("🧹 Removed markdown code fences")

print(f"Extracted {len(text)} characters")
print("\nCleaned response preview:")
print(text[:500] if text else "No text found")

# ============================================
#  CELL 5 — PARSE OR CREATE FALLBACK
# ============================================
itinerary = None
partial_data = {}

if text:
    try:
        itinerary = json.loads(text)
        print("\n✅ JSON parsed successfully")
    except json.JSONDecodeError as e:
        print(f"\n⚠️ JSON incomplete (error at char {e.pos}), extracting partial data...")
        print(f"Text length: {len(text)} chars")
        print(f"Last 100 chars: ...{text[-100:]}")
        
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        print(f"Open braces: {open_braces}, Open brackets: {open_brackets}")
        
        attempts = [
            ("original", text),
            ("add_braces", text + '}' * open_braces + ']' * open_brackets),
            ("simple_close", text.rstrip(',\n ') + ']}}'),
            ("double_close", text.rstrip(',\n ') + ']}]}'),
            ("triple_close", text.rstrip(',\n ') + '}]}}'),
        ]
        
        for method, attempt in attempts:
            try:
                partial_data = json.loads(attempt)
                print(f"✅ Extracted with '{method}': {list(partial_data.keys())}")
                if partial_data.get('flights'):
                    print(f"   ✈️  Found {len(partial_data['flights'])} flights")
                if partial_data.get('hotels'):
                    print(f"   🏨 Found {len(partial_data['hotels'])} hotels")
                if partial_data.get('attractions'):
                    print(f"   🎯 Found {len(partial_data['attractions'])} attractions")
                break
            except Exception as ex:
                print(f"   ❌ '{method}' failed: {str(ex)[:60]}")

if not itinerary:
    print("\n📝 Building final itinerary...")
    
    flights_data = partial_data.get('flights')
    hotels_data = partial_data.get('hotels')
    attractions_data = partial_data.get('attractions')
    
    if flights_data:
        print(f"✅ Using {len(flights_data)} real flights from search")
    else:
        print("ℹ️  Using template flights")
        flights_data = [
            {"airline": "IndiGo / Thai Airways", "price": "$400-600", "duration": "3-4h", "route": f"{ORIGIN}-{DESTINATION}"}
        ]
    
    if hotels_data:
        print(f"✅ Using {len(hotels_data)} real hotels from search")
    else:
        print("ℹ️  Using template hotels")
        hotels_data = [
            {"name": "Hotel recommendations", "price": "$50-150/night", "rating": "4 stars", "area": "Sukhumvit / Silom"},
            {"name": "Search booking.com", "price": "$100-200/night", "rating": "5 stars", "area": "Riverside"}
        ]
    
    if attractions_data:
        print(f"✅ Using {len(attractions_data)} real attractions from search")
    else:
        print("ℹ️  Using template attractions")
        attractions_data = [
            {"name": "Grand Palace", "cost": "$15", "type": "Temple"},
            {"name": "Wat Pho", "cost": "$5", "type": "Temple"},
            {"name": "Wat Arun", "cost": "$3", "type": "Temple"},
            {"name": "Chatuchak Market", "cost": "Free entry", "type": "Market"},
            {"name": "Chao Phraya River Cruise", "cost": "$30-50", "type": "Cruise"}
        ]
    
    itinerary = {
        "trip_summary": {
            "from": ORIGIN,
            "to": DESTINATION,
            "dates": f"{START_DATE} to {END_DATE}",
            "travelers": TRAVELERS
        },
        "flights": flights_data,
        "hotels": hotels_data,
        "attractions": attractions_data,
        "daily_plan": partial_data.get('daily_plan', [
            {"day": 1, "date": "2025-12-10", "activities": ["Arrival", "Check-in hotel", "Explore nearby area"]},
            {"day": 2, "date": "2025-12-11", "activities": ["Grand Palace", "Wat Pho", "Chatuchak Market"]},
            {"day": 3, "date": "2025-12-12", "activities": ["Wat Arun", "River cruise", "Asiatique night market"]},
            {"day": 4, "date": "2025-12-13", "activities": ["Damnoen Saduak Floating Market", "Shopping"]},
            {"day": 5, "date": "2025-12-14", "activities": ["Relaxation", "Last-minute shopping", "Prepare for departure"]},
            {"day": 6, "date": "2025-12-15", "activities": ["Check-out", "Flight back to Bangalore"]}
        ]),
        "estimated_costs": {
            "flights": "$400-600 per person",
            "hotels": "$250-500 total (5 nights)",
            "attractions": "$100-150 per person",
            "food": "$200-300 per person",
            "total": "$950-1550 per person"
        },
        "tips": [
            "Use BTS Skytrain for easy transport",
            "Download Grab app for taxis",
            "Dress modestly for temples (cover shoulders and knees)",
            "Carry small bills for markets",
            "Book river cruise in advance during peak season"
        ]
    }
    
    if partial_data:
        sources = []
        if partial_data.get('flights'):
            sources.append("flights")
        if partial_data.get('hotels'):
            sources.append("hotels")
        if partial_data.get('attractions'):
            sources.append("attractions")
        if sources:
            itinerary["data_source"] = f"Real search data: {', '.join(sources)}. Other sections: curated recommendations"

print("\n📋 Final Itinerary Summary:")
print(f"  Flights: {len(itinerary['flights'])} options")
print(f"  Hotels: {len(itinerary['hotels'])} options")
print(f"  Attractions: {len(itinerary['attractions'])} places")
print(f"  Daily plan: {len(itinerary['daily_plan'])} days")

# ============================================
#  CELL 6 — EXPORT CSV FILES
# ============================================
def safe_df(data, default_cols):
    if not data:
        return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(data)

base = f"Bangkok_Trip_{uuid.uuid4().hex[:4]}"

df1 = safe_df([itinerary.get('trip_summary', {})], ['from', 'to', 'dates', 'travelers'])
f1 = f"{base}_summary.csv"
df1.to_csv(f1, index=False)

df2 = safe_df(itinerary.get('flights', []), ['airline', 'price', 'duration'])
f2 = f"{base}_flights.csv"
df2.to_csv(f2, index=False)

df3 = safe_df(itinerary.get('hotels', []), ['name', 'price', 'rating'])
f3 = f"{base}_hotels.csv"
df3.to_csv(f3, index=False)

df4 = safe_df(itinerary.get('attractions', []), ['name', 'cost'])
f4 = f"{base}_attractions.csv"
df4.to_csv(f4, index=False)

df5 = safe_df(itinerary.get('daily_plan', []), ['day', 'date', 'activities'])
f5 = f"{base}_daily_plan.csv"
df5.to_csv(f5, index=False)

print(f"""
✅ CSV files exported:
  • {f1}
  • {f2}
  • {f3}
  • {f4}
  • {f5}
""")

# ============================================
#  CELL 7 — EXPORT EXCEL
# ============================================
excel_file = f"{base}_complete.xlsx"

with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name='Summary', index=False)
    df2.to_excel(writer, sheet_name='Flights', index=False)
    df3.to_excel(writer, sheet_name='Hotels', index=False)
    df4.to_excel(writer, sheet_name='Attractions', index=False)
    df5.to_excel(writer, sheet_name='Daily Plan', index=False)

print(f"✅ Excel file: {excel_file}")

# ============================================
#  CELL 8 — EXPORT PDF
# ============================================
pdf_file = f"{base}_itinerary.pdf"
styles = getSampleStyleSheet()
doc = SimpleDocTemplate(pdf_file)
story = []

story.append(Paragraph(f"<b>Trip to {DESTINATION}</b>", styles["Title"]))
story.append(Paragraph(f"{START_DATE} to {END_DATE}", styles["Normal"]))
story.append(Paragraph("<br/><br/>", styles["Normal"]))

for section, data in itinerary.items():
    story.append(Paragraph(f"<b>{section.replace('_', ' ').title()}</b>", styles["Heading2"]))
    story.append(Paragraph(str(data)[:400], styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

doc.build(story)
print(f"✅ PDF file: {pdf_file}")

# ============================================
#  CELL 9 — EXPORT POWERPOINT
# ============================================
ppt_file = f"{base}_presentation.pptx"
prs = Presentation()

slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = f"Trip to {DESTINATION}"
slide.placeholders[1].text = f"{START_DATE} to {END_DATE}\n{TRAVELERS} travelers"

slide2 = prs.slides.add_slide(prs.slide_layouts[1])
slide2.shapes.title.text = "Trip Details"
content = f"""Flights: {len(itinerary.get('flights', []))} options
Hotels: {len(itinerary.get('hotels', []))} recommendations  
Attractions: {len(itinerary.get('attractions', []))} places
Days: {len(itinerary.get('daily_plan', []))} day itinerary"""
slide2.placeholders[1].text = content

prs.save(ppt_file)
print(f"✅ PowerPoint file: {ppt_file}")

print(f"""
🎉 ALL EXPORTS COMPLETE!

Files created:
  📊 {excel_file} (Excel with all data)
  📄 {pdf_file} (PDF itinerary)
  🎯 {ppt_file} (PowerPoint presentation)
  📋 5 CSV files (individual sections)

Total: 8 files ready to download!
""")
