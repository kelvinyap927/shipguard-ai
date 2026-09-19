"""
ai_classifier.py — Member A

Uses Gemini AI to classify emails that the rule-based
classifier is not confident about.
"""

import json
import os
import re
import ssl
import urllib.error
import urllib.request

import certifi
from dotenv import load_dotenv


# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

load_dotenv()


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

CATEGORIES = [
    "document_comparison",
    "new_si_request",
    "invoice_query",
    "general",
    "spam",
]

GEMINI_MODEL = "gemini-3.1-flash-lite"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)


# ------------------------------------------------------------
# Prompt
# ------------------------------------------------------------

SYSTEM_PROMPT = """
You classify shipping operations emails.

Classify each email into EXACTLY ONE category:

- document_comparison:
  The sender wants a Shipping Instruction (SI) and draft
  Bill of Lading (BL) checked, compared, verified or confirmed.

- new_si_request:
  The sender provides shipping instruction information or
  requests preparation of shipping instructions.

- invoice_query:
  The email asks about invoices, billing, charges, freight,
  THC, payment or other costs.

- general:
  Normal shipping communication, operational updates,
  vessel updates, reminders or confirmations.

- spam:
  Promotional, phishing, scam or irrelevant email.

Important rules:

1. Read both the subject and body.
2. Do not rely only on the subject.
3. A document comparison email can still be document_comparison
   even if the SI or BL attachment is missing.
4. Missing attachments are handled by another part of the system.
5. Do not invent information.

Return ONLY valid JSON in this format:

{
    "category": "category_name",
    "confidence_score": 0.0,
    "reason": "short reason"
}
"""


# ------------------------------------------------------------
# Build message
# ------------------------------------------------------------

def build_user_message(email, has_si=False, has_bl=False):

    if has_si and has_bl:
        attachment_info = "SI and BL attachments present"

    elif has_si:
        attachment_info = "SI attachment present, BL missing"

    elif has_bl:
        attachment_info = "BL attachment present, SI missing"

    else:
        attachment_info = "SI and BL attachments not detected"

    return f"""
{SYSTEM_PROMPT}

EMAIL TO CLASSIFY

From:
{email.get("from", "")}

Subject:
{email.get("subject", "")}

Attachment information:
{attachment_info}

Body:
{email.get("body", "")[:1500]}
"""


# ------------------------------------------------------------
# Gemini API
# ------------------------------------------------------------

def call_gemini(user_message):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": user_message
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    data = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    request = urllib.request.Request(
        GEMINI_URL,
        data=data,
        headers=headers,
        method="POST"
    )

    ssl_context = ssl.create_default_context(
        cafile=certifi.where()
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
            context=ssl_context
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(
            f"Gemini API error {error.code}: {error_body}"
        )

    return result["candidates"][0]["content"]["parts"][0]["text"]


# ------------------------------------------------------------
# Confidence conversion
# ------------------------------------------------------------

def confidence_level(score):

    if score >= 0.80:
        return "HIGH"

    elif score >= 0.60:
        return "MEDIUM"

    else:
        return "LOW"


# ------------------------------------------------------------
# Main AI classifier
# ------------------------------------------------------------

def classify_with_ai(email, has_si=False, has_bl=False):

    user_message = build_user_message(
        email,
        has_si,
        has_bl
    )

    try:

        raw = call_gemini(user_message)

        raw = re.sub(
            r"```(?:json)?",
            "",
            raw
        ).replace("```", "").strip()

        result = json.loads(raw)

        category = result.get("category")
        score = float(
            result.get("confidence_score", 0)
        )

        if category not in CATEGORIES:
            raise ValueError(
                "Gemini returned an invalid category"
            )

        if score < 0 or score > 1:
            raise ValueError(
                "Gemini returned an invalid confidence score"
            )

        return {
            "category": category,
            "confidence": confidence_level(score),
            "confidence_score": score,
            "scores": {},
            "source": "ai",
            "provider": "gemini",
            "reason": result.get("reason", ""),
            "status": "ok"
        }

    except Exception as error:

        return {
            "category": None,
            "confidence": "LOW",
            "confidence_score": 0.0,
            "scores": {},
            "source": "ai",
            "provider": "gemini",
            "reason": str(error),
            "status": "failed"
        }