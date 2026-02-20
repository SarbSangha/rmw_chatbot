# Intent detection engine - moved from frontend

import re
from typing import Dict, Any

# ================= LEAD KEYWORDS =================
LEAD_KEYWORDS = [
    "contact", "price", "pricing", "cost", "charge", "charges", 
    "quote", "quotation", "hire", "project", "call", "email", 
    "interested", "talk", "budget", "estimate",
    "how much", "rate", "fees", "package"
]

# ================= INTENT PATTERNS =================
INTENT_PATTERNS = {
    "servicesList": [
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
}

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

# ================= SUB SERVICE MAP =================
SUB_SERVICE_MAP = {
    # ===== DIGITAL MARKETING =====
    "digital marketing": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "seo": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "ppc": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "google ads": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "social media": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "orm": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "lead generation": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    "brand awareness": """✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?""",

    # ===== CREATIVE SERVICES =====
    "creative services": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.""",

    "creative": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.""",

    "branding": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.""",

    "logo": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.""",

    "graphic": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.""",

    "packaging": """🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.""",

    # ===== PRINT ADVERTISING =====
    "print advertising": """📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling

We handle everything from design to placement in top publications.""",

    "print": """📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling

We handle everything from design to placement in top publications.""",

    "copywriting": """📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling

We handle everything from design to placement in top publications.""",

    # ===== RADIO ADVERTISING =====
    "radio advertising": """📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.""",

    "radio": """📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.""",

    "scriptwriting": """📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.""",

    "voiceover": """📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.""",

    # ===== CONTENT MARKETING =====
    "content marketing": """📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.""",

    "content": """📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.""",

    "email marketing": """📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.""",

    "newsletter": """📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.""",

    "infographic": """📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.""",

    # ===== WEB DEVELOPMENT =====
    "web development": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "web": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "ui/ux": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "uiux": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "ui ux": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "ux": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "wordpress": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "ecommerce": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "e-commerce": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "landing page": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    "website": """💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.""",

    # ===== CELEBRITY ENDORSEMENTS =====
    "celebrity endorsements": """⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance

We connect your brand with the right celebrity to amplify your message.""",

    "celebrity": """⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance

We connect your brand with the right celebrity to amplify your message.""",

    "endorsement": """⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance

We connect your brand with the right celebrity to amplify your message.""",

    # ===== INFLUENCER MARKETING =====
    "influencer marketing": """📱 Influencer Marketing Services:

1️⃣ Influencer Identification & Vetting
2️⃣ Cost-Benefit Analysis
3️⃣ Contract Negotiations
4️⃣ Creative Collaboration
5️⃣ Campaign Integration
6️⃣ Performance Tracking & Messaging Optimization

We partner with the right influencers to reach your target audience authentically.""",

    "influencer": """📱 Influencer Marketing Services:

1️⃣ Influencer Identification & Vetting
2️⃣ Cost-Benefit Analysis
3️⃣ Contract Negotiations
4️⃣ Creative Collaboration
5️⃣ Campaign Integration
6️⃣ Performance Tracking & Messaging Optimization

We partner with the right influencers to reach your target audience authentically."""
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


def detect_intent(message: str) -> Dict[str, Any]:
    """Detect user intent from message"""
    lower = message.lower()
    normalized = normalize_input(message)

    # Priority 1: Sub-services FIRST
    for key in SUB_SERVICE_MAP.keys():
        if key in lower:
            return {"type": "sub_service", "service": key}
        
        normalized_key = normalize_input(key)
        if normalized_key in normalized:
            return {"type": "sub_service", "service": key}

    # Priority 2: Services list
    has_service_intent = any(
        pattern in lower for pattern in INTENT_PATTERNS["servicesList"]
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
    intent = detect_intent(message)

    if intent["type"] == "sub_service":
        service = intent["service"]
        return {
            "answer": SUB_SERVICE_MAP[service],
            "intent": "sub_service",
            "show_lead_form": False,
            "follow_up": None
        }

    elif intent["type"] == "services_list":
        return {
            "answer": SERVICES_LIST,
            "intent": "services_list",
            "show_lead_form": False,
            "follow_up": "Which service interests you the most? Just type the name (like 'Digital Marketing' or 'Creative Services') and I'll share the details! 😊"
        }

    elif intent["type"] == "pricing_contact":
        return {
            "answer": "Our pricing is fully customized based on your goals and industry. Let me connect you with our team for a detailed proposal 👇",
            "intent": "pricing_contact",
            "show_lead_form": True,
            "follow_up": None
        }

    else:
        # Return None to indicate RAG processing needed
        return None
