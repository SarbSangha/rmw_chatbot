# app/api/v1/ui.py - UI and messaging endpoints

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/v1", tags=["ui"])


class WelcomeMessageResponse(BaseModel):
    message: str
    show_typing: bool = True
    delay: int = 800  # milliseconds


@router.get("/welcome", response_model=WelcomeMessageResponse)
async def get_welcome_message():
    """
    GET /v1/welcome
    Returns initial welcome message shown when chatbot loads
    """
    return WelcomeMessageResponse(
        message="""Hello 👋 I'm Ruby.
Welcome to Ritz Media World.

If you're exploring our services, campaigns, or capabilities,
I'm here to help you 😊""",
        show_typing=True,
        delay=800
    )


class EnquireButtonResponse(BaseModel):
    label: str
    text: str
    show_after_intent: bool


@router.get("/enquire-button", response_model=EnquireButtonResponse)
async def get_enquire_button():
    """
    GET /v1/enquire-button
    Returns enquire button configuration
    """
    return EnquireButtonResponse(
        label="Enquire",
        text="Enquire",
        show_after_intent=True
    )


class FollowUpMessageResponse(BaseModel):
    sub_service: str
    services_list: str
    pricing_contact: str
    general_error: str


@router.get("/follow-up-messages", response_model=FollowUpMessageResponse)
async def get_follow_up_messages():
    """
    GET /v1/follow-up-messages
    Returns follow-up messages used in different scenarios
    """
    return FollowUpMessageResponse(
        sub_service="Want to discuss your specific needs? I can connect you with our team 👇",
        services_list="Which service interests you the most? Just type the name (like 'Digital Marketing' or 'Creative Services') and I'll share the details! 😊",
        pricing_contact="Our pricing is fully customized based on your goals and industry. Let me connect you with our team for a detailed proposal 👇",
        general_error="⏳ Taking longer than usual. Try asking about a specific service like 'Digital Marketing' for an instant answer, or contact us directly:\n📞 +91-7290002168"
    )


class ContactInfoResponse(BaseModel):
    phone: str
    email: str
    phone_formatted: str


@router.get("/contact-info", response_model=ContactInfoResponse)
async def get_contact_info():
    """
    GET /v1/contact-info
    Returns contact information for fallback/error messages
    """
    return ContactInfoResponse(
        phone="+91-7290002168",
        email="info@ritzmediaworld.com",
        phone_formatted="📞 +91-7290002168"
    )


class ChatConfigResponse(BaseModel):
    timeout_ms: int
    typing_indicator_delay: int
    enable_caching: bool
    max_history: int


@router.get("/chat-config", response_model=ChatConfigResponse)
async def get_chat_config():
    """
    GET /v1/chat-config
    Returns chat configuration that frontend should use
    """
    return ChatConfigResponse(
        timeout_ms=12000,
        typing_indicator_delay=500,
        enable_caching=True,
        max_history=6
    )
