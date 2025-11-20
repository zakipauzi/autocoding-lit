#!/usr/bin/env python3
"""
Quick test to see OpenAI response format for debugging
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
import pdfplumber

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Extract a small sample from the PDF
with pdfplumber.open('pdfs/v93w-ytyc.pdf') as pdf:
    text = ""
    for page in pdf.pages[:3]:  # Just first 3 pages
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

# Load prompt
with open('prompt_template.txt', 'r', encoding='utf-8') as f:
    prompt = f.read()

# Test request
print("Sending request to OpenAI...")
response = client.chat.completions.create(
    model="gpt-5-mini-2025-08-07",
    messages=[
        {
            "role": "system",
            "content": "You are an expert researcher. Analyze the research paper and answer the specific questions."
        },
        {
            "role": "user", 
            "content": f"{prompt}\n\nRESEARCH PAPER:\n{text[:10000]}"  # Limit to 10k chars for test
        }
    ],
    max_completion_tokens=1500
)

print("\n" + "="*50)
print("AI RESPONSE:")
print("="*50)
print(response.choices[0].message.content)
print("="*50)