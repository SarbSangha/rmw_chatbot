// ================= CHAT CONFIGURATION =================
let chatConfig = {};
let contactInfo = {};
let formSchema = {};

async function loadChatConfig() {
    try {
        // Load chat configuration from backend
        const configRes = await fetch('/v1/chat-config');
        chatConfig = await configRes.json();
        
        // Load contact info from backend
        const contactRes = await fetch('/v1/contact-info');
        contactInfo = await contactRes.json();
        
        // Load form schema from backend
        const formRes = await fetch('/submit-lead/form-schema');
        formSchema = await formRes.json();
        
        console.log('✅ Configuration loaded', { chatConfig, contactInfo, formSchema });
    } catch (err) {
        console.error('❌ Configuration loading failed:', err);
        // Use defaults
        chatConfig = { timeout_ms: 12000, typing_indicator_delay: 500, max_history: 6 };
        contactInfo = { phone: '+91-7290002168', email: 'info@ritzmediaworld.com' };
    }
}

// Load config on script load
loadChatConfig();

// ================= CHAT STATE =================
let chatHistory = [];

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    if (!message) return;

    addMessage('You', message);
    input.value = '';

    const typingIndicator = addMessage('Bot', '', true);
    const controller = new AbortController();
    
    const timeoutId = setTimeout(() => {
        controller.abort();
        typingIndicator.remove();
        addMessage('Bot', `⏳ Taking longer than usual. Try asking about a specific service like 'Digital Marketing' for an instant answer, or contact us directly:\n📞 ${contactInfo.phone}`);
    }, chatConfig.timeout_ms || 12000);

    try {
        // Call backend message endpoint with intent detection
        const res = await fetch('/v1/message', {
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

        // Display main answer
        addMessage('Bot', data.answer, false, data.sources || []);

        // Handle follow-up message if needed
        if (data.follow_up) {
            setTimeout(() => {
                addMessage('Bot', data.follow_up);
            }, chatConfig.typing_indicator_delay || 500);
        }

        // Show lead form button if needed
        if (data.show_lead_form) {
            setTimeout(() => addEnquireButton(), chatConfig.typing_indicator_delay || 400);
        }

    } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
            console.error('❌ Chat Error:', err);
            typingIndicator.remove();
            addMessage('Bot', `⚠️ Something went wrong. Please try again or contact us:\n📞 ${contactInfo.phone}\n📧 ${contactInfo.email}`);
        }
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

    // Build form dynamically from schema
    let formHTML = '<div class="lead-content"><h3>Share your details</h3>';
    
    if (formSchema.fields) {
        formSchema.fields.forEach(field => {
            if (field.type === 'select') {
                formHTML += `
                    <select id="lead${field.id.charAt(0).toUpperCase() + field.id.slice(1)}" 
                            data-field="${field.id}" 
                            class="lead-input">
                        <option value="">${field.placeholder}</option>
                        ${field.options.map(opt => `<option>${opt}</option>`).join('')}
                    </select>`;
            } else if (field.type === 'textarea') {
                formHTML += `<textarea id="lead${field.id.charAt(0).toUpperCase() + field.id.slice(1)}" 
                                        data-field="${field.id}" 
                                        class="lead-input"
                                        placeholder="${field.placeholder}"></textarea>`;
            } else {
                formHTML += `<input id="lead${field.id.charAt(0).toUpperCase() + field.id.slice(1)}" 
                                     type="${field.type}" 
                                     data-field="${field.id}" 
                                     class="lead-input"
                                     placeholder="${field.placeholder}" />`;
            }
        });
    }
    
    formHTML += `
        <p id="leadError" class="lead-error"></p>
        <div class="lead-buttons">
            <button onclick="submitLead()">Submit</button>
            <button onclick="closeLeadModal()">Cancel</button>
        </div>
        </div>
    `;

    formWrapper.innerHTML = formHTML;
    chatBox.appendChild(formWrapper);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Add inline validation listeners
    formSchema.fields.forEach(field => {
        const fieldId = `lead${field.id.charAt(0).toUpperCase() + field.id.slice(1)}`;
        const element = document.getElementById(fieldId);
        if (element) {
            element.addEventListener('blur', () => validateField(field.id));
        }
    });
}

function closeLeadModal() {
    const inlineForm = document.getElementById('inline-lead-form');
    if (inlineForm) inlineForm.remove();
}

// ================= VALIDATION WITH BACKEND =================
async function validateField(fieldId) {
    const fieldMap = {
        'name': 'leadName',
        'phone': 'leadPhone',
        'email': 'leadEmail',
        'service': 'leadService',
        'message': 'leadMsg'
    };

    const inputElement = document.getElementById(fieldMap[fieldId]);
    if (!inputElement) return;

    const value = inputElement.value.trim();
    if (!value) return; // Skip empty optional fields

    try {
        const validationData = {};
        validationData[fieldId] = value;

        const res = await fetch('/submit-lead/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(validationData)
        });

        const result = await res.json();
        const errorBox = document.getElementById('leadError');

        if (!result.valid && result.errors[fieldId]) {
            errorBox.innerText = result.errors[fieldId];
            inputElement.style.borderColor = 'red';
        } else {
            inputElement.style.borderColor = '';
        }
    } catch (err) {
        console.error('❌ Validation Error:', err);
    }
}

async function validateAllFields() {
    const errors = {};

    try {
        const name = document.getElementById('leadName')?.value.trim() || '';
        const phone = document.getElementById('leadPhone')?.value.trim() || '';
        const email = document.getElementById('leadEmail')?.value.trim() || '';
        const service = document.getElementById('leadService')?.value || '';

        // Validate all at once
        const res = await fetch('/submit-lead/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name || undefined,
                phone: phone || undefined,
                email: email || undefined,
                service: service || undefined
            })
        });

        const result = await res.json();
        return result;
    } catch (err) {
        console.error('❌ Validation Error:', err);
        return { valid: false, errors: { general: 'Validation failed' } };
    }
}

// ================= SUBMIT LEAD =================
async function submitLead() {
    const errorBox = document.getElementById("leadError");
    
    // Validate using backend
    const validation = await validateAllFields();

    if (!validation.valid) {
        const firstError = Object.values(validation.errors)[0];
        errorBox.innerText = firstError || "Please check the form";
        return;
    }

    errorBox.innerText = "";

    const name = document.getElementById("leadName").value.trim();
    const phone = document.getElementById("leadPhone").value.trim();
    const email = document.getElementById("leadEmail").value.trim();
    const service = document.getElementById("leadService").value;
    const message = document.getElementById("leadMsg")?.value.trim() || "";

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
            if (document.getElementById("leadMsg")) {
                document.getElementById("leadMsg").value = "";
            }
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
window.addEventListener("load", async () => {
    try {
        // Load welcome message from backend
        const welcomeRes = await fetch('/v1/welcome');
        const welcomeData = await welcomeRes.json();
        
        if (welcomeData.show_typing) {
            const typing = addMessage('Bot', '', true);
            setTimeout(() => {
                typing.remove();
                addMessage('Bot', welcomeData.message);
            }, welcomeData.delay);
        } else {
            addMessage('Bot', welcomeData.message);
        }
    } catch (err) {
        console.error('❌ Welcome message error:', err);
        // Fallback welcome message
        const typing = addMessage('Bot', '', true);
        setTimeout(() => {
            typing.remove();
            addMessage('Bot', `Hello 👋 I'm Ruby.\nWelcome to Ritz Media World.\n\nIf you're exploring our services, campaigns, or capabilities,\nI'm here to help you 😊`);
        }, 800);
    }
});
