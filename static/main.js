// ================= INTENT CONFIG ================= 
const leadKeywords = [
    "contact", "price", "pricing", "cost", "charge", "charges", 
    "quote", "quotation", "hire", "project", "call", "email", 
    "interested", "talk", "budget", "estimate",
    "how much", "rate", "fees", "package"
];

let leadShown = false;

function shouldShowLeadForm(msg) {
    const text = msg.toLowerCase();
    return leadKeywords.some(k => text.includes(k));
}

// ================= INPUT NORMALIZER =================
function normalizeInput(text) {
    return text
        .toLowerCase()
        .replace(/[,\.\-\_\/]/g, ' ')  // Replace commas, dots, slashes, dashes with space
        .replace(/\s+/g, ' ')           // Collapse multiple spaces
        .trim();
}

// ================= INTENT DETECTION ENGINE =================
const intentPatterns = {
    servicesList: [
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
};

function detectIntent(message) {
    const lower = message.toLowerCase();
    const normalized = normalizeInput(message);

    // Priority 1: Sub-services FIRST (before anything else)
    for (const key in subServiceMap) {
        // Check original lowercase input
        if (lower.includes(key)) {
            return { type: 'sub_service', service: key };
        }
        // Check normalized input (catches ui,ux → ui ux, seo/ppc etc.)
        const normalizedKey = normalizeInput(key);
        if (normalized.includes(normalizedKey)) {
            return { type: 'sub_service', service: key };
        }
    }

    // Priority 2: Services list
    // Only show full list if NO specific sub-service matched
    const hasServiceIntent = intentPatterns.servicesList.some(p => lower.includes(p));
    if (hasServiceIntent) return { type: 'services_list' };

    // Priority 3: Pricing/Contact
    if (shouldShowLeadForm(message)) return { type: 'pricing_contact' };

    // Priority 4: General RAG
    return { type: 'general' };
}

// ================= MAIN SERVICES LIST =================
const servicesList = `Here are all the services we offer:

1️⃣ Digital Marketing
2️⃣ Creative Services
3️⃣ Print Advertising
4️⃣ Radio Advertising
5️⃣ Content Marketing
6️⃣ Web Development
7️⃣ Celebrity Endorsements
8️⃣ Influencer Marketing`;

// ================= SUB SERVICE MAP ================= 
const subServiceMap = {

    // ===== DIGITAL MARKETING =====
    "digital marketing": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "seo": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "ppc": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "google ads": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "social media": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "orm": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "lead generation": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    "brand awareness": `✨ Digital Marketing Services:

1️⃣ SEO (Search Engine Optimization)
2️⃣ PPC (Google Ads)
3️⃣ Social Media Management & ORM
4️⃣ Lead Generation
5️⃣ Brand Awareness

Each service is customized to your brand's goals. Want to know more about any of these?`,

    // ===== CREATIVE SERVICES =====
    "creative services": `🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.`,

    "creative": `🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.`,

    "branding": `🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.`,

    "logo": `🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.`,

    "graphic": `🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.`,

    "packaging": `🎨 Creative Services:

1️⃣ Branding & Identity Development
2️⃣ Graphic Design
3️⃣ Logo Design
4️⃣ Print Advertising Design
5️⃣ Packaging Design

We bring your brand vision to life through strategic design.`,

    // ===== PRINT ADVERTISING =====
    "print advertising": `📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling

We handle everything from design to placement in top publications.`,

    "print": `📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling

We handle everything from design to placement in top publications.`,

    "copywriting": `📰 Print Advertising Services:

1️⃣ Advertisement Design
2️⃣ Ad Placement (Newspapers, Magazines)
3️⃣ Copywriting
4️⃣ Media Buying & Cost Negotiation
5️⃣ Ad Size Optimization
6️⃣ Campaign Scheduling

We handle everything from design to placement in top publications.`,

    // ===== RADIO ADVERTISING =====
    "radio advertising": `📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.`,

    "radio": `📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.`,

    "scriptwriting": `📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.`,

    "voiceover": `📻 Radio Advertising Services:

1️⃣ Advertising Concept Development
2️⃣ Scriptwriting
3️⃣ Voiceover Casting
4️⃣ Recording & Production
5️⃣ Media Planning & Buying
6️⃣ Cost Negotiations

From script to broadcast, we create radio campaigns that capture attention.`,

    // ===== CONTENT MARKETING =====
    "content marketing": `📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.`,

    "content": `📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.`,

    "email marketing": `📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.`,

    "newsletter": `📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.`,

    "infographic": `📝 Content Marketing Services:

1️⃣ Customized Content Strategy
2️⃣ Email & Newsletter Marketing
3️⃣ Asset Creation & Infographics
4️⃣ Content Promotion & Optimization

We craft content that tells your brand story and drives engagement.`,

    // ===== WEB DEVELOPMENT =====
    "web development": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "web": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "ui/ux": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "uiux": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "ui ux": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "ux": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "wordpress": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "ecommerce": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "e-commerce": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "landing page": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    "website": `💻 Web Development Services:

1️⃣ UI/UX Design
2️⃣ Custom Website Design & Development
3️⃣ E-Commerce Website Development
4️⃣ Landing Page Development
5️⃣ WordPress Web Design

We build high-converting digital experiences, not just websites.`,

    // ===== CELEBRITY ENDORSEMENTS =====
    "celebrity endorsements": `⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance

We connect your brand with the right celebrity to amplify your message.`,

    "celebrity": `⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance

We connect your brand with the right celebrity to amplify your message.`,

    "endorsement": `⭐ Celebrity Endorsement Services:

1️⃣ Celebrity Identification & Selection
2️⃣ Contract Negotiations
3️⃣ Creative Collaboration
4️⃣ Campaign Integration
5️⃣ Public Relations Management
6️⃣ Legal Compliance

We connect your brand with the right celebrity to amplify your message.`,

    // ===== INFLUENCER MARKETING =====
    "influencer marketing": `📱 Influencer Marketing Services:

1️⃣ Influencer Identification & Vetting
2️⃣ Cost-Benefit Analysis
3️⃣ Contract Negotiations
4️⃣ Creative Collaboration
5️⃣ Campaign Integration
6️⃣ Performance Tracking & Messaging Optimization

We partner with the right influencers to reach your target audience authentically.`,

    "influencer": `📱 Influencer Marketing Services:

1️⃣ Influencer Identification & Vetting
2️⃣ Cost-Benefit Analysis
3️⃣ Contract Negotiations
4️⃣ Creative Collaboration
5️⃣ Campaign Integration
6️⃣ Performance Tracking & Messaging Optimization

We partner with the right influencers to reach your target audience authentically.`
};

// ================= HELPERS =================
function checkSubServices(message) {
    const lower = message.toLowerCase();
    const normalized = normalizeInput(message);

    // Check original keys first
    for (const key in subServiceMap) {
        if (lower.includes(key)) return subServiceMap[key];
    }

    // Check normalized input (catches ui,ux / ui-ux / seo,ppc etc.)
    for (const key in subServiceMap) {
        const normalizedKey = normalizeInput(key);
        if (normalized.includes(normalizedKey)) return subServiceMap[key];
    }

    return null;
}

// ================= CHAT FUNCTION ================= 
let chatHistory = [];

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    if (!message) return;

    addMessage('You', message);
    input.value = '';

    // 🎯 Detect intent
    const intent = detectIntent(message);
    console.log('🎯 Detected Intent:', intent);

    switch (intent.type) {

        case 'sub_service':
            addMessage('Bot', subServiceMap[intent.service]);
            setTimeout(() => {
                addMessage('Bot', "Want to discuss your specific needs? I can connect you with our team 👇");
                addEnquireButton();
            }, 500);
            break;

        case 'services_list':
            addMessage('Bot', servicesList);
            setTimeout(() => {
                addMessage('Bot', "Which service interests you the most? Just type the name (like 'Digital Marketing' or 'Creative Services') and I'll share the details! 😊");
            }, 600);
            break;

        case 'pricing_contact':
            addMessage('Bot', "Our pricing is fully customized based on your goals and industry. Let me connect you with our team for a detailed proposal 👇");
            setTimeout(() => addEnquireButton(), 400);
            break;

        case 'general':
        default:
            const typingIndicator = addMessage('Bot', '', true);

            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                controller.abort();
                typingIndicator.remove();
                addMessage('Bot', "⏳ Taking longer than usual. Try asking about a specific service like 'Digital Marketing' for an instant answer, or contact us directly:\n📞 +91-7290002168");
            }, 12000);

            try {
                const res = await fetch('/v1/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: message,
                        session_id: null 
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);
                const data = await res.json();
                typingIndicator.remove();

                addMessage('Bot', data.answer, false, data.sources || []);

                if (!leadShown && shouldShowLeadForm(data.answer || message)) {
                    setTimeout(() => {
                        addMessage('Bot', "Want to discuss this further? I can connect you with our team 👇");
                        addEnquireButton();
                    }, 500);
                }

            } catch (err) {
                clearTimeout(timeoutId);
                if (err.name !== 'AbortError') {
                    console.error('❌ Chat Error:', err);
                    typingIndicator.remove();
                    addMessage('Bot', '⚠️ Something went wrong. Please try again or contact us:\n📞 +91-7290002168\n📧 info@ritzmediaworld.com');
                }
            }
            break;
    }
}

// ================= MESSAGE UI =================
function addMessage(sender, text, isTyping = false, sources = []) {
    const chatBox = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.className = 'message ' + (sender === 'You' ? 'user-message' : 'bot-message');

    if (isTyping) {
        msg.innerHTML = `<div class="typing"><span></span><span></span><span></span></div>`;
    } else {
        msg.textContent = text;

        if (!isTyping && text) {
            chatHistory.push({ role: sender === 'You' ? 'user' : 'assistant', content: text });
            if (chatHistory.length > 6) chatHistory.shift();
        }

        if (sources.length > 0) {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'bot-source';
            sourceDiv.textContent = `Source: ${sources.join(' | ')}`;
            msg.appendChild(sourceDiv);
        }
    }

    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
}

// ================= ENQUIRE BUTTON =================
function addEnquireButton() {
    const chatBox = document.getElementById('chat-box');

    const wrapper = document.createElement('div');
    wrapper.className = 'message bot-message';

    const btn = document.createElement('button');
    btn.innerText = "Enquire";
    btn.className = "enquire-btn";

    btn.onclick = () => {
        openLeadModal();
        leadShown = true;
    };

    wrapper.appendChild(btn);
    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ================= LEAD FORM INLINE =================
function openLeadModal() {
    const existingForm = document.getElementById('inline-lead-form');
    if (existingForm) {
        existingForm.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    const chatBox = document.getElementById('chat-box');

    const formWrapper = document.createElement('div');
    formWrapper.className = 'message bot-message inline-lead-form-wrapper';
    formWrapper.id = 'inline-lead-form';

    formWrapper.innerHTML = `
        <div class="lead-content">
            <h3>Share your details</h3>
            <input id="leadName" placeholder="Name *" />
            <input id="leadPhone" placeholder="Phone Number *" />
            <input id="leadEmail" placeholder="Email Address *" />
            <select id="leadService">
                <option value="">Select Service *</option>
                <option>Digital Marketing</option>
                <option>Creative Services</option>
                <option>Print Advertising</option>
                <option>Radio Advertising</option>
                <option>Content Marketing</option>
                <option>Web Development</option>
                <option>Celebrity Endorsements</option>
                <option>Influencer Marketing</option>
            </select>
            <textarea id="leadMsg" placeholder="Message (optional)"></textarea>
            <p id="leadError" class="lead-error"></p>
            <div class="lead-buttons">
                <button onclick="submitLead()">Submit</button>
                <button onclick="closeLeadModal()">Cancel</button>
            </div>
        </div>
    `;

    chatBox.appendChild(formWrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function closeLeadModal() {
    const inlineForm = document.getElementById('inline-lead-form');
    if (inlineForm) inlineForm.remove();
}

// ================= VALIDATION =================
function validateLead() {
    const name = document.getElementById("leadName").value.trim();
    const phone = document.getElementById("leadPhone").value.trim();
    const email = document.getElementById("leadEmail").value.trim();
    const service = document.getElementById("leadService").value;

    if (name.length < 3 || !/^[a-zA-Z ]+$/.test(name))
        return "Name must have at least 3 letters (alphabets only)";

    if (!/^\d{10}$/.test(phone))
        return "Phone must be exactly 10 digits";

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
        return "Invalid email format";

    if (!service)
        return "Please select a service";

    return null;
}

// ================= SUBMIT LEAD =================
async function submitLead() {
    const errorBox = document.getElementById("leadError");
    const error = validateLead();

    if (error) {
        errorBox.innerText = error;
        return;
    }

    errorBox.innerText = "";

    const name = document.getElementById("leadName").value.trim();
    const phone = document.getElementById("leadPhone").value.trim();
    const email = document.getElementById("leadEmail").value.trim();
    const service = document.getElementById("leadService").value;
    const message = document.getElementById("leadMsg").value.trim();

    try {
        const response = await fetch("/submit-lead", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, phone, email, service, message })
        });

        const result = await response.json();

        if (result.success) {
            closeLeadModal();
            addMessage("Bot", "✅ Thanks! Our team will reach out soon 🙂");
            document.getElementById("leadName").value = "";
            document.getElementById("leadPhone").value = "";
            document.getElementById("leadEmail").value = "";
            document.getElementById("leadService").value = "";
            document.getElementById("leadMsg").value = "";
        } else {
            errorBox.innerText = result.message || "Submission failed";
        }
    } catch (err) {
        console.error(err);
        errorBox.innerText = "Network error — please try again.";
    }
}

// ================= ENTER KEY =================
document.getElementById('user-input')
    .addEventListener('keypress', function (e) {
        if (e.key === 'Enter') sendMessage();
    });

// ================= AUTO WELCOME =================
window.addEventListener("load", () => {
    const typing = addMessage('Bot', '', true);
    setTimeout(() => {
        typing.remove();
        addMessage('Bot',
            `Hello 👋 I'm Ruby.
Welcome to Ritz Media World.

If you're exploring our services, campaigns, or capabilities,
I'm here to help you 😊`
        );
    }, 800);
});
