import os
import sys
import time
import json
import urllib.parse
import feedparser
from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient
from supabase import create_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ["VITE_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
APIFY_TOKEN  = os.environ["APIFY_TOKEN"]
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
apify    = ApifyClient(APIFY_TOKEN)

try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except ImportError:
    groq_client = None

MAX_RESULTS_PER_COMPANY = 5

# How far back to look for NEW posts on each scrape. Daily cron sets this to
# 1 to fetch only the last 24 h delta. Manual backfills can set it to 7.
SCRAPE_WINDOW_DAYS = int(os.environ.get("SCRAPE_WINDOW_DAYS", "1"))

# How long to keep rows in the DB before purging. Independent of the scrape
# window — short window + longer retention = daily delta on a rolling feed.
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "7"))

# Apify's LinkedIn actor accepts "past-24h", "past-week", "past-month".
APIFY_DATE_POSTED = "past-24h" if SCRAPE_WINDOW_DAYS <= 1 else "past-week"

# ── UAE news sites ────────────────────────────────────────────────────────────
# Direct UAE publisher feeds. Khaleej Times exposes RSS via a hidden API
# (discovered through the homepage's <link rel="alternate"> tags). The
# National uses Arc Publishing's outbound feed. Arabian Business and
# Gulf Business expose news sitemaps.
HTTP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

NEWS_RSS_FEEDS = [
    # Khaleej Times
    ("Khaleej Times", "Business",
     "https://www.khaleejtimes.com/api/v1/collections/business.rss", "UAE"),
    ("Khaleej Times", "UAE",
     "https://www.khaleejtimes.com/api/v1/collections/uae.rss", "UAE"),
    ("Khaleej Times", "Top",
     "https://www.khaleejtimes.com/api/v1/collections/top-section.rss", "UAE"),
    # The National
    ("The National", "Business",
     "https://www.thenationalnews.com/arc/outboundfeeds/rss/category/business/?outputType=xml", "UAE"),
    ("The National", "All",
     "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml", "UAE"),
]

NEWS_SITEMAPS = [
    ("Arabian Business", "https://www.arabianbusiness.com/news-sitemap.xml", "UAE"),
    ("Gulf Business",    "https://gulfbusiness.com/sitemap.xml",             "UAE"),
]

# Strict insurance filter. Multi-word phrases avoid the false positives we
# saw with single words like "risk" (war risk, health risk) and "policy"
# (visa policy, fuel policy).
INSURANCE_STRONG = [
    "insurance", "insurer", "insurers", "reinsurance", "reinsurer",
    "takaful", "retakaful", "underwriting", "underwriter",
    "actuarial", "actuary", "policyholder", "premium income",
    "claims ratio", "loss ratio", "combined ratio", "solvency",
    "insurance company", "insurance market", "insurance sector",
    "insurance authority", "insurance regulation", "insurance broker",
    "insurance premium", "insurance claim", "general insurance",
    "life insurance", "health insurance", "motor insurance",
    "property insurance", "marine insurance", "cyber insurance",
    "travel insurance",
]


def matches_insurance(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in INSURANCE_STRONG)

# ── Topic classification keywords ─────────────────────────────────────────────
TOPIC_KEYWORDS = {
    "Technical": [
        "ai", "artificial intelligence", "machine learning", "insurtech",
        "digital", "technology", "automation", "data analytics", "algorithm",
        "blockchain", "telematics", "iot", "internet of things", "platform",
        "cloud", "cyber", "api", "software", "app", "mobile", "innovation",
        "parametric", "model", "predictive", "claims technology",
    ],
    "Regulatory": [
        "regulat", "compliance", "circular", "directive", "legislation",
        "law", "authority", "government", "mandate", "requirement",
        "solvency", "capital requirement", "license", "licenc", "sanction",
        "central bank", "ministry", "decree", "ifrs", "gdpr", "aml",
        "anti-money laundering", "insurance authority", "supervisory",
        "enforcement", "penalty", "fine", "audit",
    ],
}
# Anything that doesn't match Technical or Regulatory defaults to Business

def classify_topic(text: str) -> str:
    text_lower = (text or "").lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return topic
    return "Business"


# ── Full directory: "Region|Type" → [{name, url, slug}] ───────────────────────
DIRECTORY = {
    "UAE|Insurer": [
        {"name": "ADNIC", "url": "https://linkedin.com/company/adnic", "slug": "adnic"},
        {"name": "Emirates Insurance Company", "url": "https://linkedin.com/company/emirates-insurance-company", "slug": "emirates-insurance-company"},
        {"name": "Orient Insurance", "url": "https://linkedin.com/company/orient-insurance-company", "slug": "orient-insurance-company"},
        {"name": "Sukoon Insurance", "url": "https://linkedin.com/company/sukoon-insurance", "slug": "sukoon-insurance"},
        {"name": "GIG Gulf", "url": "https://linkedin.com/company/gig-gulf", "slug": "gig-gulf"},
        {"name": "Alliance Insurance", "url": "https://linkedin.com/company/alliance-insurance-psc", "slug": "alliance-insurance-psc"},
        {"name": "Daman National Health Insurance", "url": "https://linkedin.com/company/daman", "slug": "daman"},
        {"name": "National General Insurance NGI", "url": "https://linkedin.com/company/national-general-insurance", "slug": "national-general-insurance"},
        {"name": "Dubai Insurance Company", "url": "https://linkedin.com/company/dubai-insurance-company", "slug": "dubai-insurance-company"},
        {"name": "Dubai National Insurance Reinsurance", "url": "https://linkedin.com/company/dubai-national-insurance-reinsurance", "slug": "dubai-national-insurance-reinsurance"},
        {"name": "Al Wathba National Insurance AWNIC", "url": "https://linkedin.com/company/al-wathba-national-insurance", "slug": "al-wathba-national-insurance"},
        {"name": "Watania Takaful", "url": "https://linkedin.com/company/watania", "slug": "watania"},
        {"name": "Abu Dhabi National Takaful ADNTC", "url": "https://linkedin.com/company/abu-dhabi-national-takaful", "slug": "abu-dhabi-national-takaful"},
        {"name": "Al Buhaira National Insurance", "url": "https://linkedin.com/company/al-buhaira-national-insurance", "slug": "al-buhaira-national-insurance"},
        {"name": "Al Khazna Insurance", "url": "https://linkedin.com/company/al-khazna-insurance", "slug": "al-khazna-insurance"},
        {"name": "Al Dhafra Insurance", "url": "https://linkedin.com/company/al-dhafra-insurance", "slug": "al-dhafra-insurance"},
        {"name": "Al Sagr National Insurance", "url": "https://linkedin.com/company/al-sagr-national-insurance", "slug": "al-sagr-national-insurance"},
        {"name": "Salama Islamic Arab Insurance", "url": "https://linkedin.com/company/salama-islamic-arab-insurance", "slug": "salama-islamic-arab-insurance"},
        {"name": "Arabia Insurance", "url": "https://linkedin.com/company/arabia-insurance", "slug": "arabia-insurance"},
        {"name": "Liva Insurance", "url": "https://linkedin.com/company/liva-insurance", "slug": "liva-insurance"},
        {"name": "MetLife UAE insurance", "url": "https://linkedin.com/company/metlife", "slug": "metlife"},
        {"name": "Allianz Trade Middle East insurance", "url": "https://linkedin.com/company/allianz-trade", "slug": "allianz-trade"},
        {"name": "MEDGULF insurance UAE", "url": "https://linkedin.com/company/medgulf", "slug": "medgulf"},
        {"name": "Bupa Global Middle East insurance", "url": "https://linkedin.com/company/bupa-global", "slug": "bupa-global"},
        {"name": "Cigna Middle East insurance", "url": "https://linkedin.com/company/cigna", "slug": "cigna"},
    ],
    "UAE|Broker": [
        {"name": "Marsh UAE insurance broker", "url": "https://linkedin.com/company/marsh-uae", "slug": "marsh-uae"},
        {"name": "Aon Middle East insurance broker", "url": "https://linkedin.com/company/aon", "slug": "aon"},
        {"name": "WTW Willis Towers Watson insurance", "url": "https://linkedin.com/company/wtw", "slug": "wtw"},
        {"name": "Lockton MENA insurance broker", "url": "https://linkedin.com/company/lockton", "slug": "lockton"},
        {"name": "Howden Insurance Brokers UAE", "url": "https://linkedin.com/company/howdengroup", "slug": "howdengroup"},
        {"name": "Nexus Insurance Brokers UAE", "url": "https://linkedin.com/company/nexus-insurance-brokers", "slug": "nexus-insurance-brokers"},
        {"name": "Al Nabooda Insurance Brokers", "url": "https://linkedin.com/company/al-nabooda-insurance-brokers", "slug": "al-nabooda-insurance-brokers"},
        {"name": "Indemnity Insurance Brokers UAE", "url": "https://linkedin.com/company/indemnity-insurance-brokers", "slug": "indemnity-insurance-brokers"},
        {"name": "Master Insurance Brokers UAE", "url": "https://linkedin.com/company/master-insurance-brokers", "slug": "master-insurance-brokers"},
        {"name": "JK Risk Managers Insurance Brokers", "url": "https://linkedin.com/company/j-k-risk-managers", "slug": "j-k-risk-managers"},
        {"name": "Lifecare International Insurance Brokers", "url": "https://linkedin.com/company/lifecare-international", "slug": "lifecare-international"},
        {"name": "Malakut Insurance Brokers", "url": "https://linkedin.com/company/malakut-insurance-brokers", "slug": "malakut-insurance-brokers"},
        {"name": "Kay International insurance AMEA", "url": "https://linkedin.com/company/kay-international", "slug": "kay-international"},
    ],
    "UAE|Re-Broker": [
        {"name": "Shields Reinsurance Brokers DIFC", "url": "https://linkedin.com/company/shields-reinsurance", "slug": "shields-reinsurance"},
        {"name": "Howden Re DIFC reinsurance", "url": "https://linkedin.com/company/howden-re", "slug": "howden-re"},
        {"name": "Guy Carpenter MENA reinsurance", "url": "https://linkedin.com/company/guy-carpenter", "slug": "guy-carpenter"},
        {"name": "Lockton Re DIFC reinsurance", "url": "https://linkedin.com/company/lockton-re", "slug": "lockton-re"},
        {"name": "Kingdom Brokerage Re DIFC", "url": "https://linkedin.com/company/kingdom-brokerage-re", "slug": "kingdom-brokerage-re"},
    ],
    "UAE|Reinsurer": [
        {"name": "Munich Re UAE DIFC reinsurance", "url": "https://linkedin.com/company/munich-re", "slug": "munich-re"},
        {"name": "Swiss Re UAE reinsurance", "url": "https://linkedin.com/company/swiss-re", "slug": "swiss-re"},
        {"name": "SCOR UAE reinsurance", "url": "https://linkedin.com/company/scor", "slug": "scor"},
        {"name": "IGI International General Insurance", "url": "https://linkedin.com/company/igi", "slug": "igi"},
        {"name": "Korean Re DIFC reinsurance", "url": "https://linkedin.com/company/korean-re", "slug": "korean-re"},
        {"name": "Malaysian Re Dubai reinsurance", "url": "https://linkedin.com/company/malaysian-re", "slug": "malaysian-re"},
        {"name": "Mena Re Underwriters reinsurance", "url": "https://linkedin.com/company/mena-re", "slug": "mena-re"},
        {"name": "Emirates Retakaful reinsurance", "url": "https://linkedin.com/company/emirates-retakaful", "slug": "emirates-retakaful"},
    ],
    "UAE|Aggregator": [
        {"name": "Policybazaar UAE insurance", "url": "https://linkedin.com/company/policybazaar-uae", "slug": "policybazaar-uae"},
        {"name": "YallaCompare insurance UAE", "url": "https://linkedin.com/company/yallacompare", "slug": "yallacompare"},
        {"name": "Aqeed insurance UAE", "url": "https://linkedin.com/company/aqeed", "slug": "aqeed"},
        {"name": "Bayzat insurance UAE", "url": "https://linkedin.com/company/bayzat", "slug": "bayzat"},
        {"name": "Souqalmal insurance UAE", "url": "https://linkedin.com/company/souqalmal", "slug": "souqalmal"},
        {"name": "InsuranceMarket.ae UAE", "url": "https://linkedin.com/company/insurancemarket-ae", "slug": "insurancemarket-ae"},
    ],
    "UAE|Consultancy": [
        {"name": "KPMG Lower Gulf insurance consulting", "url": "https://linkedin.com/company/kpmg-lower-gulf", "slug": "kpmg-lower-gulf"},
        {"name": "PwC Middle East insurance consulting", "url": "https://linkedin.com/company/pwc-middle-east", "slug": "pwc-middle-east"},
        {"name": "Deloitte Middle East insurance", "url": "https://linkedin.com/company/deloitte-middle-east", "slug": "deloitte-middle-east"},
        {"name": "EY MENA insurance consulting", "url": "https://linkedin.com/company/ey-mena", "slug": "ey-mena"},
        {"name": "McKinsey Middle East insurance", "url": "https://linkedin.com/company/mckinsey-middle-east", "slug": "mckinsey-middle-east"},
        {"name": "BCG Middle East insurance consulting", "url": "https://linkedin.com/company/bcg-middle-east", "slug": "bcg-middle-east"},
        {"name": "Bain Company Middle East insurance", "url": "https://linkedin.com/company/bain-company-middle-east", "slug": "bain-company-middle-east"},
        {"name": "Oliver Wyman Dubai insurance", "url": "https://linkedin.com/company/oliver-wyman", "slug": "oliver-wyman"},
        {"name": "ValuStrat insurance UAE", "url": "https://linkedin.com/company/valustrat", "slug": "valustrat"},
        {"name": "Redseer Strategy Consultants insurance", "url": "https://linkedin.com/company/redseer", "slug": "redseer"},
    ],
    "GCC|Insurer": [
        {"name": "Qatar Insurance Group QIG", "url": "https://linkedin.com/company/qatar-insurance-group", "slug": "qatar-insurance-group"},
        {"name": "Gulf Insurance Group GIG", "url": "https://linkedin.com/company/gulf-insurance-group", "slug": "gulf-insurance-group"},
        {"name": "Tawuniya insurance Saudi Arabia", "url": "https://linkedin.com/company/tawuniya", "slug": "tawuniya"},
        {"name": "Bupa Arabia health insurance", "url": "https://linkedin.com/company/bupa-arabia", "slug": "bupa-arabia"},
        {"name": "Malath Cooperative Insurance Saudi", "url": "https://linkedin.com/company/malath-insurance", "slug": "malath-insurance"},
        {"name": "Medgulf Saudi Arabia insurance", "url": "https://linkedin.com/company/medgulf", "slug": "medgulf"},
        {"name": "AXA Cooperative Insurance Saudi", "url": "https://linkedin.com/company/axa", "slug": "axa"},
        {"name": "Liva Group Oman insurance", "url": "https://linkedin.com/company/liva-group", "slug": "liva-group"},
        {"name": "Bahrain Kuwait Insurance BKI", "url": "https://linkedin.com/company/bahrain-kuwait-insurance", "slug": "bahrain-kuwait-insurance"},
    ],
    "GCC|Reinsurer": [
        {"name": "Arab Insurance Group ARIG reinsurance", "url": "https://linkedin.com/company/arab-insurance-group", "slug": "arab-insurance-group"},
        {"name": "Hannover Re Bahrain reinsurance", "url": "https://linkedin.com/company/hannover-re", "slug": "hannover-re"},
    ],
    "Europe|Insurer": [
        {"name": "Allianz insurance Germany", "url": "https://linkedin.com/company/allianz", "slug": "allianz"},
        {"name": "AXA insurance France", "url": "https://linkedin.com/company/axa", "slug": "axa"},
        {"name": "Generali insurance Italy", "url": "https://linkedin.com/company/assicurazioni-generali", "slug": "assicurazioni-generali"},
        {"name": "Zurich Insurance Group", "url": "https://linkedin.com/company/zurich-insurance-group", "slug": "zurich-insurance-group"},
        {"name": "Aviva insurance UK", "url": "https://linkedin.com/company/aviva", "slug": "aviva"},
        {"name": "Prudential plc insurance", "url": "https://linkedin.com/company/prudential-plc", "slug": "prudential-plc"},
        {"name": "Legal General insurance UK", "url": "https://linkedin.com/company/legal-general", "slug": "legal-general"},
        {"name": "Hiscox insurance", "url": "https://linkedin.com/company/hiscox", "slug": "hiscox"},
        {"name": "Beazley insurance", "url": "https://linkedin.com/company/beazley", "slug": "beazley"},
        {"name": "Lloyds of London insurance market", "url": "https://linkedin.com/company/lloyds-of-london", "slug": "lloyds-of-london"},
        {"name": "MAPFRE insurance", "url": "https://linkedin.com/company/mapfre", "slug": "mapfre"},
        {"name": "Talanx HDI Group insurance", "url": "https://linkedin.com/company/talanx", "slug": "talanx"},
        {"name": "Liberty Specialty Markets insurance", "url": "https://linkedin.com/company/liberty-specialty-markets", "slug": "liberty-specialty-markets"},
    ],
    "Europe|Reinsurer": [
        {"name": "Munich Re reinsurance", "url": "https://linkedin.com/company/munich-re", "slug": "munich-re"},
        {"name": "Swiss Re reinsurance", "url": "https://linkedin.com/company/swiss-re", "slug": "swiss-re"},
        {"name": "Hannover Re reinsurance", "url": "https://linkedin.com/company/hannover-re", "slug": "hannover-re"},
        {"name": "SCOR reinsurance", "url": "https://linkedin.com/company/scor", "slug": "scor"},
        {"name": "General Re Gen Re reinsurance", "url": "https://linkedin.com/company/gen-re", "slug": "gen-re"},
    ],
    "Europe|Broker": [
        {"name": "Marsh insurance broker global", "url": "https://linkedin.com/company/marsh", "slug": "marsh"},
        {"name": "Aon insurance broker global", "url": "https://linkedin.com/company/aon", "slug": "aon"},
        {"name": "WTW Willis Towers Watson broker", "url": "https://linkedin.com/company/wtw", "slug": "wtw"},
        {"name": "Gallagher Arthur J Gallagher insurance", "url": "https://linkedin.com/company/ajg", "slug": "ajg"},
        {"name": "Howden Group insurance broker", "url": "https://linkedin.com/company/howdengroup", "slug": "howdengroup"},
    ],
    "Europe|Re-Broker": [
        {"name": "BMS Group reinsurance broker", "url": "https://linkedin.com/company/bms-group", "slug": "bms-group"},
        {"name": "Guy Carpenter reinsurance broker global", "url": "https://linkedin.com/company/guy-carpenter", "slug": "guy-carpenter"},
        {"name": "Howden Re reinsurance broker global", "url": "https://linkedin.com/company/howden-re", "slug": "howden-re"},
    ],
    "Americas|Insurer": [
        {"name": "State Farm insurance USA", "url": "https://linkedin.com/company/state-farm", "slug": "state-farm"},
        {"name": "Berkshire Hathaway GEICO insurance", "url": "https://linkedin.com/company/berkshire-hathaway", "slug": "berkshire-hathaway"},
        {"name": "Progressive insurance USA", "url": "https://linkedin.com/company/progressive-insurance", "slug": "progressive-insurance"},
        {"name": "Allstate insurance USA", "url": "https://linkedin.com/company/allstate", "slug": "allstate"},
        {"name": "Chubb insurance", "url": "https://linkedin.com/company/chubb", "slug": "chubb"},
        {"name": "AIG American International Group insurance", "url": "https://linkedin.com/company/aig", "slug": "aig"},
        {"name": "Liberty Mutual insurance", "url": "https://linkedin.com/company/liberty-mutual-insurance", "slug": "liberty-mutual-insurance"},
        {"name": "Travelers insurance USA", "url": "https://linkedin.com/company/the-travelers-companies", "slug": "the-travelers-companies"},
        {"name": "MetLife insurance Americas", "url": "https://linkedin.com/company/metlife", "slug": "metlife"},
        {"name": "Prudential Financial insurance", "url": "https://linkedin.com/company/prudential-financial", "slug": "prudential-financial"},
        {"name": "UnitedHealth Group insurance", "url": "https://linkedin.com/company/unitedhealthgroup", "slug": "unitedhealthgroup"},
        {"name": "CNA Financial insurance", "url": "https://linkedin.com/company/cna-financial", "slug": "cna-financial"},
        {"name": "Manulife Financial insurance Canada", "url": "https://linkedin.com/company/manulife", "slug": "manulife"},
        {"name": "Sun Life Financial insurance Canada", "url": "https://linkedin.com/company/sun-life-financial", "slug": "sun-life-financial"},
        {"name": "Intact Financial insurance Canada", "url": "https://linkedin.com/company/intact-financial-corporation", "slug": "intact-financial-corporation"},
    ],
    "Americas|Reinsurer": [
        {"name": "Everest Re reinsurance", "url": "https://linkedin.com/company/everest-re", "slug": "everest-re"},
        {"name": "RenaissanceRe reinsurance", "url": "https://linkedin.com/company/renaissancere", "slug": "renaissancere"},
        {"name": "RGA Reinsurance Group America", "url": "https://linkedin.com/company/rga", "slug": "rga"},
    ],
    "Americas|Broker": [
        {"name": "Marsh McLennan insurance broker", "url": "https://linkedin.com/company/marsh-mclennan", "slug": "marsh-mclennan"},
        {"name": "Aon insurance broker Americas", "url": "https://linkedin.com/company/aon", "slug": "aon"},
        {"name": "Lockton insurance broker", "url": "https://linkedin.com/company/lockton", "slug": "lockton"},
        {"name": "Brown Brown insurance broker", "url": "https://linkedin.com/company/brown-brown-insurance", "slug": "brown-brown-insurance"},
    ],
    "Africa|Insurer": [
        {"name": "Sanlam insurance South Africa", "url": "https://linkedin.com/company/sanlam", "slug": "sanlam"},
        {"name": "Old Mutual insurance South Africa", "url": "https://linkedin.com/company/old-mutual", "slug": "old-mutual"},
        {"name": "Discovery insurance South Africa", "url": "https://linkedin.com/company/discovery", "slug": "discovery"},
        {"name": "Santam insurance South Africa", "url": "https://linkedin.com/company/santam", "slug": "santam"},
        {"name": "Hollard Insurance South Africa", "url": "https://linkedin.com/company/hollard-insurance", "slug": "hollard-insurance"},
        {"name": "Momentum Metropolitan insurance", "url": "https://linkedin.com/company/momentum-metropolitan", "slug": "momentum-metropolitan"},
        {"name": "Liberty Holdings insurance Africa", "url": "https://linkedin.com/company/liberty-holdings", "slug": "liberty-holdings"},
        {"name": "Jubilee Insurance East Africa", "url": "https://linkedin.com/company/jubilee-insurance", "slug": "jubilee-insurance"},
        {"name": "Leadway Assurance Nigeria insurance", "url": "https://linkedin.com/company/leadway-assurance", "slug": "leadway-assurance"},
        {"name": "AIICO Insurance Nigeria", "url": "https://linkedin.com/company/aiico-insurance", "slug": "aiico-insurance"},
        {"name": "AXA Mansard Nigeria insurance", "url": "https://linkedin.com/company/axa-mansard", "slug": "axa-mansard"},
        {"name": "SanlamAllianz Africa insurance", "url": "https://linkedin.com/company/sanlamallianz", "slug": "sanlamallianz"},
    ],
    "Africa|Reinsurer": [
        {"name": "Munich Re Africa reinsurance", "url": "https://linkedin.com/company/munich-re", "slug": "munich-re"},
    ],
    "South Asia|Insurer": [
        {"name": "LIC Life Insurance Corporation India", "url": "https://linkedin.com/company/lic-of-india", "slug": "lic-of-india"},
        {"name": "ICICI Lombard General Insurance India", "url": "https://linkedin.com/company/icici-lombard", "slug": "icici-lombard"},
        {"name": "ICICI Prudential Life Insurance India", "url": "https://linkedin.com/company/icici-prudential-life", "slug": "icici-prudential-life"},
        {"name": "Bajaj Allianz Insurance India", "url": "https://linkedin.com/company/bajaj-allianz", "slug": "bajaj-allianz"},
        {"name": "HDFC ERGO General Insurance India", "url": "https://linkedin.com/company/hdfc-ergo", "slug": "hdfc-ergo"},
        {"name": "New India Assurance insurance", "url": "https://linkedin.com/company/new-india-assurance", "slug": "new-india-assurance"},
        {"name": "SBI General Insurance India", "url": "https://linkedin.com/company/sbi-general-insurance", "slug": "sbi-general-insurance"},
        {"name": "Tata AIG General Insurance India", "url": "https://linkedin.com/company/tata-aig", "slug": "tata-aig"},
        {"name": "State Life Insurance Pakistan", "url": "https://linkedin.com/company/state-life-insurance", "slug": "state-life-insurance"},
        {"name": "Jubilee Life Insurance Pakistan", "url": "https://linkedin.com/company/jubilee-life-insurance", "slug": "jubilee-life-insurance"},
        {"name": "AIA Group insurance Asia", "url": "https://linkedin.com/company/aia-group", "slug": "aia-group"},
        {"name": "Ping An Insurance China", "url": "https://linkedin.com/company/ping-an-insurance", "slug": "ping-an-insurance"},
    ],
    "Global|Consultancy": [
        {"name": "McKinsey Company insurance consulting", "url": "https://linkedin.com/company/mckinsey", "slug": "mckinsey"},
        {"name": "Boston Consulting Group BCG insurance", "url": "https://linkedin.com/company/boston-consulting-group", "slug": "boston-consulting-group"},
        {"name": "Bain Company insurance consulting", "url": "https://linkedin.com/company/bain-and-company", "slug": "bain-and-company"},
        {"name": "Deloitte insurance practice consulting", "url": "https://linkedin.com/company/deloitte", "slug": "deloitte"},
        {"name": "PwC insurance practice consulting", "url": "https://linkedin.com/company/pwc", "slug": "pwc"},
        {"name": "KPMG insurance practice consulting", "url": "https://linkedin.com/company/kpmg", "slug": "kpmg"},
        {"name": "EY Ernst Young insurance consulting", "url": "https://linkedin.com/company/ernst-young", "slug": "ernst-young"},
        {"name": "Accenture insurance consulting", "url": "https://linkedin.com/company/accenture", "slug": "accenture"},
        {"name": "Oliver Wyman insurance consulting", "url": "https://linkedin.com/company/oliver-wyman", "slug": "oliver-wyman"},
        {"name": "Roland Berger insurance consulting", "url": "https://linkedin.com/company/roland-berger", "slug": "roland-berger"},
        {"name": "Strategy PwC insurance consulting", "url": "https://linkedin.com/company/strategyand", "slug": "strategyand"},
        {"name": "Kearney insurance consulting", "url": "https://linkedin.com/company/at-kearney", "slug": "at-kearney"},
        {"name": "Arthur D Little insurance consulting", "url": "https://linkedin.com/company/arthur-d-little", "slug": "arthur-d-little"},
        {"name": "EY Parthenon insurance consulting", "url": "https://linkedin.com/company/ey-parthenon", "slug": "ey-parthenon"},
        {"name": "Capgemini insurance consulting", "url": "https://linkedin.com/company/capgemini", "slug": "capgemini"},
        {"name": "Majesco insurance technology", "url": "https://linkedin.com/company/majesco", "slug": "majesco"},
        {"name": "Clyde Co insurance legal", "url": "https://linkedin.com/company/clyde-co", "slug": "clyde-co"},
    ],
}

# ── Hiring filter ──────────────────────────────────────────────────────────────
HIRING_KEYWORDS = [
    "we're hiring", "we are hiring", "job opening", "job opportunity",
    "apply now", "join our team", "open position", "career opportunity",
    "now recruiting", "looking for a ", "looking for an ",
    "vacancy", "vacancies", "job posting", "applications open",
    "we are looking for", "send your cv", "send your resume",
]

def is_hiring_post(text: str) -> bool:
    return any(kw in (text or "").lower() for kw in HIRING_KEYWORDS)


# ── Author match ───────────────────────────────────────────────────────────────
def post_is_from_company(item: dict, slug: str) -> bool:
    post_url    = (item.get("post_url") or "").lower()
    author      = item.get("author") or {}
    author_url  = (author.get("profile_url") or author.get("company_url") or "").lower() \
                  if isinstance(author, dict) else ""
    author_name = (author.get("name") or "").lower() if isinstance(author, dict) else ""

    slug_lower    = slug.lower()
    slug_spaced   = slug_lower.replace("-", " ")
    slug_nohyphen = slug_lower.replace("-", "")

    return (
        slug_lower    in post_url     or
        slug_spaced   in post_url     or
        slug_lower    in author_url   or
        slug_spaced   in author_name  or
        slug_nohyphen in author_name
    )


# ── LinkedIn fetch ─────────────────────────────────────────────────────────────
def fetch_company_posts(company: dict) -> list:
    try:
        run = apify.actor("apimaestro/linkedin-posts-search-scraper-no-cookies").call(
            run_input={
                "keyword":    company["name"],
                "sortBy":     "date_posted",
                "datePosted": APIFY_DATE_POSTED,
                "maxResults": MAX_RESULTS_PER_COMPANY,
            },
            timeout_secs=90,
        )
        items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
        return [i for i in items if post_is_from_company(i, company["slug"])]
    except Exception as e:
        print(f"      ✗ Error: {e}")
        return []


# ── Timestamp parser ───────────────────────────────────────────────────────────
def parse_timestamp(raw) -> str:
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(raw, dict):
        raw = raw.get("date") or raw.get("display_text") or ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(raw), fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).isoformat()
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    s   = str(raw).lower()
    for unit, delta in [("hour", timedelta(hours=1)), ("day", timedelta(days=1)), ("week", timedelta(weeks=1))]:
        if unit in s:
            n = int(''.join(filter(str.isdigit, s)) or 1)
            return (now - n * delta).isoformat()
    return now.isoformat()


def is_within_window(ts: str) -> bool:
    """True if `ts` is within SCRAPE_WINDOW_DAYS of now."""
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= datetime.now(timezone.utc) - timedelta(days=SCRAPE_WINDOW_DAYS)
    except Exception:
        return True


# ── Row builder (LinkedIn) ─────────────────────────────────────────────────────
def build_linkedin_row(item: dict, region: str, entity_type: str):
    url = item.get("post_url", "")
    if not url or "linkedin.com" not in url:
        return None
    text = item.get("text") or ""
    if is_hiring_post(text):
        return None
    published_at = parse_timestamp(item.get("posted_at", {}))
    if not is_within_window(published_at):
        return None

    author      = item.get("author", {})
    author_name = author.get("name") if isinstance(author, dict) else None
    title       = text[:120] + "..." if len(text) > 120 else text
    snippet     = text[:300] + "..." if len(text) > 300 else text
    topic       = classify_topic(text)

    return {
        "url":          url,
        "title":        title,
        "snippet":      snippet,
        "author":       author_name,
        "published_at": published_at,
        "category":     f"{region} | {entity_type}",
        "topic":        topic,
        "source":       "linkedin",
    }


# ── News scraper (direct UAE publisher RSS + sitemaps) ────────────────────────
import urllib.request
from xml.etree import ElementTree as ET

SITEMAP_NS = {
    "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "n": "http://www.google.com/schemas/sitemap-news/0.9",
}


def _http_get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": HTTP_UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _parse_rss_published(entry) -> str:
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def _scrape_rss_feed(publisher: str, section: str, feed_url: str, region: str,
                     seen_urls: set) -> list:
    rows = []
    try:
        body = _http_get(feed_url)
    except Exception as e:
        print(f"   ✗ {publisher} / {section}: {e}")
        return rows
    feed = feedparser.parse(body)
    for entry in feed.entries:
        title   = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or entry.get("description") or "").strip()
        url     = (entry.get("link") or "").strip()
        if not url or url in seen_urls:
            continue
        if not matches_insurance(f"{title} {summary}"):
            continue
        published_at = _parse_rss_published(entry)
        if not is_within_window(published_at):
            continue
        seen_urls.add(url)
        rows.append({
            "url":          url,
            "title":        title[:120],
            "snippet":      (summary or title)[:300],
            "author":       publisher,
            "published_at": published_at,
            "category":     f"{region} | News",
            "topic":        classify_topic(f"{title}. {summary}"),
            "source":       "news",
        })
    return rows


def _scrape_news_sitemap(publisher: str, sitemap_url: str, region: str,
                         seen_urls: set) -> list:
    rows = []
    try:
        body = _http_get(sitemap_url)
        root = ET.fromstring(body)
    except Exception as e:
        print(f"   ✗ {publisher} sitemap: {e}")
        return rows
    for u in root.findall("s:url", SITEMAP_NS):
        loc   = (u.findtext("s:loc", "", SITEMAP_NS) or "").strip()
        title = (u.findtext(".//n:title", "", SITEMAP_NS) or "").strip()
        date  = (u.findtext(".//n:publication_date", "", SITEMAP_NS)
                 or u.findtext("s:lastmod", "", SITEMAP_NS) or "").strip()
        if not loc or loc in seen_urls:
            continue
        # Title-based filter (sitemap entries have no body); also accept hits
        # in the URL slug since news sitemaps often have descriptive slugs.
        if not matches_insurance(f"{title} {loc}"):
            continue
        published_at = parse_timestamp(date) if date else datetime.now(timezone.utc).isoformat()
        if not is_within_window(published_at):
            continue
        seen_urls.add(loc)
        rows.append({
            "url":          loc,
            "title":        (title or loc)[:120],
            "snippet":      (title or loc)[:300],
            "author":       publisher,
            "published_at": published_at,
            "category":     f"{region} | News",
            "topic":        classify_topic(title),
            "source":       "news",
        })
    return rows


def scrape_news_feeds():
    print("\n── News Feeds (UAE publishers)")
    rows      = []
    seen_urls = set()

    for publisher, section, url, region in NEWS_RSS_FEEDS:
        before = len(rows)
        rows.extend(_scrape_rss_feed(publisher, section, url, region, seen_urls))
        print(f"   {publisher} / {section}: {len(rows) - before} articles")

    for publisher, url, region in NEWS_SITEMAPS:
        before = len(rows)
        rows.extend(_scrape_news_sitemap(publisher, url, region, seen_urls))
        print(f"   {publisher} (sitemap): {len(rows) - before} articles")

    inserted = upsert_posts(rows)
    print(f"   News total inserted: {inserted}\n")
    return inserted


# ── Groq AI enrichment ────────────────────────────────────────────────────────
VALID_TOPICS = {"Business", "Technical", "Regulatory"}

# Phrases the model emits when it gives up on thin content; we treat any of
# these as a degenerate output and downgrade the row to empty.
DEGENERATE_MARKERS = (
    "no substantive", "no information", "insight pending",
    "no relevant", "not provided", "no further details",
    "no specific", "no content provided",
)


def _is_degenerate(headline: str, summary: str) -> bool:
    h = (headline or "").lower()
    s = (summary  or "").lower()
    # The model sometimes produces "Insurance News" as a placeholder headline
    if h.strip() in {"insurance news", "news", "untitled", "no information"}:
        return True
    if any(m in s for m in DEGENERATE_MARKERS):
        return True
    if any(m in h for m in DEGENERATE_MARKERS):
        return True
    return False


AI_PROMPT_HEADER = (
    "You are an insurance industry analyst writing for a market-intelligence feed. "
    "You will receive a news/social post as a TITLE and BODY. The TITLE is "
    "always your primary signal — news headlines are written to convey the "
    "story. If BODY is empty, contains only HTML/markup, or is just a link, "
    "synthesize the headline and summary FROM THE TITLE ALONE.\n\n"
    "Produce three fields:\n"
    "  - headline: a concise, professional rewrite of the title (max 90 chars, no quotes, no emoji, no hashtags). "
    "Make it specific — name the company, country, or product mentioned in the title.\n"
    "  - summary:  a 1-2 sentence executive summary (max 240 chars) of what the story is about. "
    "If the body has detail, draw on it. If not, expand the title into a complete sentence stating who/what/where. "
    "NEVER write \"no substantive information\", \"insight pending\", or similar meta-comments — if you cannot "
    "summarize, write an empty string instead.\n"
    "  - topic:    EXACTLY one of \"Business\", \"Technical\", \"Regulatory\".\n\n"
    "Topic definitions (pick the single best fit):\n"
    "  * Regulatory — laws, circulars, supervisory action, licensing, compliance, central-bank / "
    "insurance-authority directives, sanctions, IFRS, AML, audits, fines, court rulings.\n"
    "  * Technical — technology, AI / ML, insurtech, digital platforms, automation, data analytics, "
    "telematics, IoT, cyber, parametric / predictive models, claims-tech, mobile apps.\n"
    "  * Business — everything else with substantive insurance content: financial results, M&A, "
    "leadership changes, product launches, partnerships, market trends, pricing, distribution.\n\n"
    "Only set headline AND summary to empty strings (\"\") when the content is purely promotional "
    "(holiday greetings, generic ads, recruiting posts) or contains zero insurance-relevant info.\n\n"
    'Respond with ONLY valid JSON: {"headline": "...", "summary": "...", "topic": "..."}\n'
)


def generate_ai_content(title: str, body: str = "") -> dict | None:
    if not groq_client:
        return None
    title = (title or "").strip()
    body  = (body  or "").strip()
    if not title and not body:
        return None
    prompt = (
        f"{AI_PROMPT_HEADER}\n"
        f"TITLE: {title[:500]}\n"
        f"BODY: {body[:2200]}"
    )
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=350,
        )
        data = json.loads(resp.choices[0].message.content)
        headline = (data.get("headline") or "").strip()
        summary  = (data.get("summary")  or "").strip()
        topic    = (data.get("topic")    or "").strip().title()
        if topic not in VALID_TOPICS:
            topic = "Business"
        if _is_degenerate(headline, summary):
            headline, summary = "", ""
        return {
            "headline": headline[:200],
            "summary":  summary[:500],
            "topic":    topic,
        }
    except Exception as e:
        print(f"      Groq error: {e}")
        return None


def enrich_with_ai(limit: int = 200) -> int:
    if not groq_client:
        print("\n⚠ GROQ_API_KEY not set or groq package missing — skipping AI enrichment\n")
        return 0
    resp = (
        supabase.table("linkedin_posts")
        .select("id, title, snippet")
        .is_("ai_headline", "null")
        .limit(limit)
        .execute()
    )
    pending = resp.data or []
    print(f"\n── AI enrichment ({len(pending)} posts pending, model={GROQ_MODEL})")
    enriched = 0
    skipped  = 0
    for row in pending:
        title   = (row.get("title")   or "").strip()
        snippet = (row.get("snippet") or "").strip()
        if not title and not snippet:
            continue
        ai = generate_ai_content(title, snippet)
        if ai is None:
            # Groq call failed — leave NULL so next run retries
            continue
        supabase.table("linkedin_posts").update({
            "ai_headline": ai["headline"],
            "ai_summary":  ai["summary"],
            "topic":       ai["topic"],
        }).eq("id", row["id"]).execute()
        if ai["headline"] or ai["summary"]:
            enriched += 1
        else:
            skipped += 1
        time.sleep(0.25)
    print(f"   AI enriched: {enriched}, skipped-as-promotional: {skipped}\n")
    return enriched


# ── Upsert ─────────────────────────────────────────────────────────────────────
def upsert_posts(rows: list) -> int:
    if not rows:
        return 0
    resp = (
        supabase.table("linkedin_posts")
        .upsert(rows, on_conflict="url_hash", ignore_duplicates=True)
        .execute()
    )
    return len(resp.data)


# ── Main ───────────────────────────────────────────────────────────────────────
def run_scraper(region_filter: str = None, type_filter: str = None):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    supabase.table("linkedin_posts").delete().lt("scraped_at", cutoff).execute()
    print(f"Purged posts older than {RETENTION_DAYS} days. "
          f"Scraping window: last {SCRAPE_WINDOW_DAYS} day(s).\n")

    grand_total = 0
    total_runs  = 0

    # ── LinkedIn scrape ────────────────────────────────────────────────────────
    for key, companies in DIRECTORY.items():
        region, entity_type = key.split("|")

        if region_filter and region != region_filter:
            continue
        if type_filter and entity_type != type_filter:
            continue

        print(f"── {region} | {entity_type} ({len(companies)} companies)")
        seen_urls = set()
        cat_total = 0

        for company in companies:
            print(f"   {company['name']}...")
            items      = fetch_company_posts(company)
            total_runs += 1
            rows = []
            for item in items:
                url = item.get("post_url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    row = build_linkedin_row(item, region, entity_type)
                    if row:
                        rows.append(row)
            inserted   = upsert_posts(rows)
            cat_total += inserted
            print(f"   → matched={len(items)}, inserted={inserted}")
            time.sleep(1)

        print(f"   Subtotal: {cat_total}\n")
        grand_total += cat_total

    # ── News RSS scrape ────────────────────────────────────────────────────────
    # Only run news scraper on full runs or UAE/GCC filters
    if not type_filter and (not region_filter or region_filter in ("UAE", "GCC")):
        grand_total += scrape_news_feeds()

    # ── AI enrichment (headline + summary) ─────────────────────────────────────
    enrich_with_ai()

    print(f"✓ Done. LinkedIn actor runs: {total_runs} | Total inserted: {grand_total}")
    return grand_total


if __name__ == "__main__":
    # `python scraper.py ai`       → only run AI enrichment on existing rows
    # `python scraper.py news`     → only run news feeds + AI
    # `python scraper.py UAE`      → only scrape UAE companies (+ news + AI)
    # `python scraper.py UAE Insurer` → narrow to UAE Insurers
    if len(sys.argv) > 1 and sys.argv[1].lower() == "ai":
        enrich_with_ai(limit=int(sys.argv[2]) if len(sys.argv) > 2 else 200)
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "news":
        scrape_news_feeds()
        enrich_with_ai()
    else:
        r = sys.argv[1] if len(sys.argv) > 1 else None
        t = sys.argv[2] if len(sys.argv) > 2 else None
        run_scraper(region_filter=r, type_filter=t)