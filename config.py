import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')  # Default to gpt-4o
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))

# File Paths
PDF_FOLDER = 'pdfs'
OUTPUT_FOLDER = 'output'
PROMPT_FILE = 'prompt_template.txt'

# CSV Column Headers (based on your coding schema)
CSV_COLUMNS = [
    'Title',
    '1.1 Primary Stakeholders',
    '1.2 Context', 
    '1.3 Tech/AI type',
    '1.4 Tool/Platform',
    '1.5 Education level',
    '2.1 Feedback term',
    '2.2 Description of context',
    '2.3 Our evaluation',
    '3.1 Agency type',
    '3.2 Feedback timing control',
    '4.1 Metrics for evaluation',
    '4.2 Measurement of agency'
]

# Processing Configuration
MAX_TEXT_LENGTH = 200000  # Increased limit - most papers will fit
CHUNK_SIZE = 100000  # Larger chunks for better context
MAX_CONTEXT_TOKENS = 120000  # Conservative token limit for gpt-4o-mini (128k context)