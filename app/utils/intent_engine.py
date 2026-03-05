# Intent detection engine - moved from frontend

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ================= SAFETY RULES =================
# Only restrict the categories specified by the product owner.
RESTRICTED_TOPICS = [
    # Alcohol
    "alcohol",
    # Drugs / narcotics
    "drug", "drugs", "narcotic", "narcotics",
    # Smoking / tobacco
    "smoking", "tobacco", "cigarette", "vape",
    # Sexual / nudity / pornography / adult services
    "nudity", "nude", "sexual", "sex", "porn", "pornography", "adult", "escort",
    # Gambling
    "gambling",
    # Violence / weapons / illegal activities
    "violence", "weapon", "weapons", "illegal",
    # Hate speech / political / religious / abusive
    "hate", "politic", "political", "religion", "abusive", "offensive",
]

RESTRICTED_RESPONSE = """I'm sorry, but I cannot assist with that request. 
If you have any business-related questions, I'd be happy to help."""


def check_safety(message: str) -> Optional[Dict[str, Any]]:
    """
    Check if the message contains restricted topics.
    Returns a response dict if restricted, None if safe.
    """
    message_lower = message.lower()
    logger.info(f"🔒 Safety check for: {message[:80]}")
    
    for topic in RESTRICTED_TOPICS:
        if topic in message_lower:
            logger.warning(f"⚠️ RESTRICTED TOPIC DETECTED: {topic} in message: {message[:80]}")
            return {
                "answer": RESTRICTED_RESPONSE,
                "intent": "restricted",
                "show_lead_form": False,
                "follow_up": None,
                "enquiry_message": None
            }
    
    logger.info(f"✅ Message is safe - no restricted topics found")
    return None


# ================= LEAD KEYWORDS =================
LEAD_KEYWORDS = [
    "contact", "price", "pricing", "cost", "charge", "charges", 
    "quote", "quotation", "hire", "project", "call", "email", 
    "interested", "talk", "budget", "estimate",
    "how much", "rate", "fees", "package"
]

# ================= EXTERNAL QUERY INDICATORS =================
# Keywords that indicate user is asking about EXTERNAL info, not your services
EXTERNAL_QUERY_INDICATORS = [
    "in delhi", "in ncr", "in india", "in mumbai", "in bangalore", 
    "in hyderabad", "in chennai", "in pune", "in kolkata",
    "top best", "list of", "agencies", "companies", "firms",
    "near me", "around me", "in area", "in market",
    "fm channels", "radio stations", "news papers", "newspapers",
    "advertising agencies", "marketing agencies"
]

# ================= SERVICES LIST PATTERNS =================
# Only match these if NOT an external query
SERVICES_LIST_PATTERNS = [
    'service', 'services',
    'what do you do', 'what do you offer', 'what you do', 'what you offer',
    'what can you', 'what are your',
    'tell me about', 'tell me more',
    'list', 'details', 'offerings',
    'how can you help', 'help me with',
    'your company', 'about ritz', 'about you',
    'all service', 'complete service',
    'show me', 'available service'
]

# ================= MAIN SERVICES LIST =================
SERVICES_LIST = """Here are all the services we offer:

1️⃣ Digital Marketing
2️⃣ Creative Services
3️⃣ Print Advertising
4️⃣ Radio Advertising
5️⃣ Content Marketing
6️⃣ Web Development
7️⃣ Celebrity Endorsements
8️⃣ Influencer Marketing"""

# ================= SELF-IDENTIFICATION PATTERNS =================
# Patterns that trigger self-identification as Ritz Media World / RMW
SELF_ID_PATTERNS = [
    "who are you",
    "what is your name",
    "who is ruby",
    "are you",
    "your name",
    "tell about yourself",
    "about yourself",
    "what company",
    "which company",
    "who is this",
    "what brand",
    "which brand",
    "what organization",
    "which organization",
    "rits media",
    "ritz media",
    "ritzwmedia",
    "rmw",
    "ritzmediaworld",
    "ritz media world"
]

SELF_ID_QUERY_CUES = [
    "who are you",
    "who is ruby",
    "what is your name",
    "your name",
    "about yourself",
    "tell about yourself",
    "what company are you",
    "which company are you",
    "who is this",
]

SELF_ID_RESPONSE = """Hello! 👋 I'm Ruby, the AI assistant for Ritz Media World (RMW).

We're a full-service marketing agency specializing in:
✨ Digital Marketing (SEO, PPC, Social Media)
🎨 Creative Services (Branding, Graphic Design)
📰 Print & Radio Advertising
💻 Web Development
⭐ Celebrity & Influencer Marketing

How can I help you today? 😊"""

# ================= GREETINGS =================
GREETING_PATTERNS = {
    "hi", "hello", "hey", "hii", "helo", "yo", "good morning", "good afternoon", "good evening"
}

GREETING_RESPONSE = """Hi! 👋 I'm Ruby from Ritz Media World.

I can help with:
1) Services and capabilities
2) Campaign ideas
3) Pricing/contact support

What would you like to explore?"""

# ================= SUB SERVICE MAP =================
SUB_SERVICE_MAP = {
    # ===== 8 MAIN SERVICES (NO DUPLICATES) =====
    "digital marketing": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness""",

    "creative services": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design""",

    "print advertising": """📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling""",

    "radio advertising": """📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations""",

    "content marketing": """📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization""",

    "web development": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design""",

    "celebrity endorsements": """⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance""",

    "influencer marketing": """📱 Influencer Marketing Services:

1️⃣ Influencer Identification & Vetting
2️⃣ Cost-Benefit Analysis
3️⃣ Contract Negotiations
4️⃣ Creative Collaboration
5️⃣ Campaign Integration
6️⃣ Performance Tracking & Messaging Optimization"""
,

    # ===== COMMON USER WORDING / SYNONYMS =====
    "social media": """Social Media Management Services:

1) Platform Strategy and Planning
2) Content Calendars and Creative Posts
3) Community Management and ORM
4) Paid Social Campaigns
5) Weekly Optimization and Reporting""",

    "performance ads": """Performance Marketing Services:

1) Google and Meta Ads Setup
2) Campaign Funnel Design
3) Audience Targeting and Retargeting
4) Budget Optimization focused on CPL and ROAS
5) Conversion Tracking and Reporting""",

    "lead generation": """Lead Generation Services:

1) ICP and Offer Strategy
2) Landing Page and Form Optimization
3) Paid Campaign Execution
4) Lead Quality Filtering
5) CPL Optimization and Scale-up""",

    "video production": """Video Production (Creative Services):

1) Concept and Script Development
2) Shoot Planning and Production
3) Editing and Motion Graphics
4) Ad Variants for Reels, YouTube, and Social
5) Delivery in Campaign-ready Formats"""

}


def normalize_input(text: str) -> str:
    """Normalize input text for matching"""
    text = text.lower()
    text = text.replace(",", " ")
    text = text.replace(".", " ")
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    return text.strip()


def should_show_lead_form(message: str) -> bool:
    """Check if message contains lead-related keywords"""
    text = message.lower()
    return any(keyword in text for keyword in LEAD_KEYWORDS)


def is_external_query(message: str) -> bool:
    """
    Check if the user is asking about external information (not your services).
    Returns True if query is about external info like local businesses, rankings, etc.
    """
    lower = message.lower()

    for pattern in EXTERNAL_QUERY_INDICATORS:
        escaped = re.escape(pattern).replace(r"\ ", r"\s+")
        regex = rf"\b{escaped}\b"
        if re.search(regex, lower):
            return True

    return False


def is_self_identification_query(message: str) -> bool:
    """
    Keep self-id intent strict so brand-specific factual questions
    (e.g., "ritz media founded in which year") still go to RAG.
    """
    normalized = normalize_input(message)

    if any(cue in normalized for cue in SELF_ID_QUERY_CUES):
        return True

    # Brand mention alone is not enough. Require clear self-id phrasing.
    if ("ritz media" in normalized or "ritz media world" in normalized or normalized == "rmw") and (
        "who are" in normalized or "about you" in normalized or "your name" in normalized
    ):
        return True

    return False


def detect_intent(message: str) -> Dict[str, Any]:
    """Detect user intent from message"""
    lower = message.lower()
    normalized = normalize_input(message)
    
    # FIRST: Check for self-identification (strict)
    if is_self_identification_query(message):
        logger.info("🏷️ Self-identification query matched")
        return {"type": "self_id"}
    
    # SECOND: Check if this is an external query - if yes, skip all service matching
    if is_external_query(message):
        return {"type": "general"}

    # THIRD: Lightweight greeting intent
    if normalized in GREETING_PATTERNS:
        return {"type": "greeting"}

    # Priority 1: Sub-services (only if NOT external query)
    for key in SUB_SERVICE_MAP.keys():
        if key in lower:
            return {"type": "sub_service", "service": key}
        
        normalized_key = normalize_input(key)
        if normalized_key in normalized:
            return {"type": "sub_service", "service": key}

    # Priority 2: Services list (only if NOT external query)
    has_service_intent = any(
        pattern in lower for pattern in SERVICES_LIST_PATTERNS
    )
    if has_service_intent:
        return {"type": "services_list"}

    # Priority 3: Pricing/Contact
    if should_show_lead_form(message):
        return {"type": "pricing_contact"}

    # Priority 4: General RAG
    return {"type": "general"}


def get_intent_response(message: str) -> Dict[str, Any]:
    """Get response based on intent detection"""
    logger.info(f"🧠 Intent Analysis: {message[:80]}")
    
    # First check safety/restricted topics
    safety_check = check_safety(message)
    if safety_check:
        logger.info(f"🛑 Safety check blocked message, returning refusal")
        return safety_check
    
    intent = detect_intent(message)
    logger.info(f"📊 Detected intent: {intent}")

    if intent["type"] == "sub_service":
        service = intent["service"]
        logger.info(f"📦 Sub-service match: {service}")
        return {
            "answer": SUB_SERVICE_MAP[service],
            "intent": "sub_service",
            "show_lead_form": False,
            "follow_up": None,
        }

    elif intent["type"] == "services_list":
        logger.info(f"📋 Services list request")
        return {
            "answer": SERVICES_LIST,
            "intent": "services_list",
            "show_lead_form": False,
            "follow_up": "Which service interests you the most? Just type the name (like 'Digital Marketing' or 'Creative Services') and I'll share the details! 😊",
        }

    elif intent["type"] == "pricing_contact":
        logger.info(f"💰 Pricing/contact intent detected")
        return {
            "answer": "Our pricing is fully customized based on your goals and industry. Let me connect you with our team for a detailed proposal 👇",
            "intent": "pricing_contact",
            "show_lead_form": True,
            "follow_up": None,
        }

    elif intent["type"] == "self_id":
        logger.info(f"🏷️ Self-identification response")
        return {
            "answer": SELF_ID_RESPONSE,
            "intent": "self_id",
            "show_lead_form": False,
            "follow_up": None,
        }

    elif intent["type"] == "greeting":
        logger.info("👋 Greeting response")
        return {
            "answer": GREETING_RESPONSE,
            "intent": "greeting",
            "show_lead_form": False,
            "follow_up": None,
        }

    else:
        # Return None to indicate RAG processing needed
        logger.info(f"🌐 General query - routing to RAG")
        return None
