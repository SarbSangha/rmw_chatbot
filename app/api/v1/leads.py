# app/api/v1/leads.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
import logging
import httpx
import re
from typing import Optional, List

router = APIRouter()
logger = logging.getLogger(__name__)

class LeadRequest(BaseModel):
    name: str = Field(..., min_length=3)
    phone: str
    email: EmailStr
    service: str
    message: str = ""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Name must contain only letters and spaces, at least 3 characters"""
        if not re.match(r'^[a-zA-Z\s]{3,}$', v):
            raise ValueError('Name must be at least 3 letters and contain only alphabets')
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Indian phone number: must start with 6/7/8/9 and be exactly 10 digits"""
        # Remove any spaces, dashes, or special characters
        clean_phone = re.sub(r'[^\d]', '', v)
        
        # Check if exactly 10 digits
        if len(clean_phone) != 10:
            raise ValueError('Phone number must be exactly 10 digits')
        
        # Check if starts with 6, 7, 8, or 9
        if not clean_phone[0] in ['6', '7', '8', '9']:
            raise ValueError('Phone number must start with 6, 7, 8, or 9')
        
        # Check if all characters are digits
        if not clean_phone.isdigit():
            raise ValueError('Phone number must contain only digits')
        
        return clean_phone
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Email validation (handled by EmailStr, but we can add custom checks)"""
        email_lower = v.lower().strip()
        
        # Block common fake/test emails
        blocked_domains = ['test.com', 'example.com', 'fake.com', 'dummy.com']
        domain = email_lower.split('@')[1] if '@' in email_lower else ''
        
        if domain in blocked_domains:
            raise ValueError('Please use a valid email address')
        
        return email_lower


# ================= NEW ENDPOINTS =================

class FormField(BaseModel):
    id: str
    label: str
    type: str
    placeholder: str
    required: bool = True
    options: Optional[List[str]] = None


class FormSchemaResponse(BaseModel):
    fields: List[FormField]
    services: List[str]


@router.get("/form-schema", response_model=FormSchemaResponse)
async def get_form_schema():
    """
    GET /submit-lead/form-schema
    Returns the structure of the lead form
    """
    services = [
        "Digital Marketing",
        "Creative Services",
        "Print Advertising",
        "Radio Advertising",
        "Content Marketing",
        "Web Development",
        "Celebrity Endorsements",
        "Influencer Marketing"
    ]
    
    fields = [
        FormField(
            id="name",
            label="Name",
            type="text",
            placeholder="Name *",
            required=True
        ),
        FormField(
            id="phone",
            label="Phone Number",
            type="tel",
            placeholder="Phone Number *",
            required=True
        ),
        FormField(
            id="email",
            label="Email Address",
            type="email",
            placeholder="Email Address *",
            required=True
        ),
        FormField(
            id="service",
            label="Service",
            type="select",
            placeholder="Select Service *",
            required=True,
            options=services
        ),
        FormField(
            id="message",
            label="Message",
            type="textarea",
            placeholder="Message (optional)",
            required=False
        )
    ]
    
    return FormSchemaResponse(fields=fields, services=services)


class ValidationRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    service: Optional[str] = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: dict = {}


@router.post("/validate", response_model=ValidationResponse)
async def validate_lead(data: ValidationRequest):
    """
    POST /submit-lead/validate
    Validates individual form fields and returns errors
    """
    errors = {}
    
    # Validate name
    if data.name is not None:
        if len(data.name.strip()) < 3:
            errors['name'] = "Name must have at least 3 letters"
        elif not re.match(r'^[a-zA-Z\s]+$', data.name):
            errors['name'] = "Name must contain only letters"
    
    # Validate phone
    if data.phone is not None:
        clean_phone = re.sub(r'[^\d]', '', data.phone)
        if len(clean_phone) != 10:
            errors['phone'] = "Phone must be exactly 10 digits"
        elif clean_phone[0] not in ['6', '7', '8', '9']:
            errors['phone'] = "Phone must start with 6, 7, 8, or 9"
    
    # Validate email
    if data.email is not None:
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, data.email):
            errors['email'] = "Invalid email format"
        else:
            blocked_domains = ['test.com', 'example.com', 'fake.com', 'dummy.com']
            domain = data.email.split('@')[1].lower()
            if domain in blocked_domains:
                errors['email'] = "Please use a valid email address"
    
    # Validate service
    if data.service is not None:
        valid_services = [
            "Digital Marketing", "Creative Services", "Print Advertising",
            "Radio Advertising", "Content Marketing", "Web Development",
            "Celebrity Endorsements", "Influencer Marketing"
        ]
        if data.service not in valid_services:
            errors['service'] = "Please select a valid service"
    
    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors
    )

@router.post("")
async def submit_lead(lead: LeadRequest):
    """
    Forward lead submissions to RMW API endpoint
    Validates: Name (3+ letters), Phone (10 digits starting with 6/7/8/9), Email
    """
    try:
        # Format message as per RMW API structure
        formatted_message = f"Service: {lead.service}\n\nQuery: {lead.message}" if lead.message else f"Service: {lead.service}"
        
        # Prepare payload matching RMW API format
        payload = {
            "etype": "ContactUs",
            "name": lead.name,
            "email": lead.email,
            "mobile": lead.phone,
            "message": formatted_message,
            "category": None,
            "resume": None
        }
        
        logger.info(f"📤 Submitting lead: {lead.name} | {lead.phone} | {lead.email}")
        
        # Send POST request to RMW API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ritzmediaworld.com/api/system-settings/contact-enquiry",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Check if request was successful
            if response.status_code in [200, 201]:
                logger.info(f"✅ Lead submitted successfully: {lead.name}")
                return {
                    "success": True,
                    "message": "Thanks! Our team will reach out soon."
                }
            else:
                logger.error(f"❌ RMW API Error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "message": "Submission failed. Please try again."
                }
                
    except httpx.TimeoutException:
        logger.error("⏰ RMW API Timeout")
        return {
            "success": False,
            "message": "Request timeout. Please try again."
        }
    except Exception as e:
        logger.error(f"💥 Lead submission error: {str(e)}")
        return {
            "success": False,
            "message": "Submission failed. Please try again."
        }
