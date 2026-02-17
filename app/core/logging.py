# app/core/logging.py
import logging

# Configure root logger once
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger("chatbot")
