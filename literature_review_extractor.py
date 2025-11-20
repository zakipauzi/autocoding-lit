#!/usr/bin/env python3
"""
Literature Review AI Coding Extractor

This script processes PDF files containing research papers and uses OpenAI's API
to extract structured coding information for literature review purposes.
It reads PDFs from a specified folder, extracts text, sends it to OpenAI for analysis,
and saves the results in a CSV file.
"""

import os
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
import pdfplumber
from openai import OpenAI
from tqdm import tqdm

from config import (
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_TEMPERATURE,
    PDF_FOLDER, OUTPUT_FOLDER, PROMPT_FILE, CSV_COLUMNS,
    MAX_TEXT_LENGTH, CHUNK_SIZE, MAX_CONTEXT_TOKENS
)


class LiteratureReviewExtractor:
    """Main class for extracting coding information from research papers."""
    
    def __init__(self):
        """Initialize the extractor with OpenAI client and logging."""
        self.setup_logging()
        self.client = self._initialize_openai_client()
        self.prompt_template = self._load_prompt_template()
        
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('literature_extraction.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_openai_client(self) -> OpenAI:
        """Initialize OpenAI client with API key validation."""
        if not OPENAI_API_KEY:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file"
            )
        
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            # Test the connection
            client.models.list()
            self.logger.info("OpenAI client initialized successfully")
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def _load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        try:
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                template = f.read().strip()
            self.logger.info(f"Loaded prompt template from {PROMPT_FILE}")
            return template
        except FileNotFoundError:
            self.logger.error(f"Prompt template file {PROMPT_FILE} not found")
            raise
        except Exception as e:
            self.logger.error(f"Error loading prompt template: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file using pdfplumber."""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Log the full extraction without truncation
            self.logger.info(f"Extracted {len(text)} characters from {pdf_path}")
            
            # Only warn if extremely long (but don't truncate)
            if len(text) > MAX_TEXT_LENGTH:
                self.logger.warning(f"Large document detected ({len(text)} chars). Will use smart processing.")
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def get_paper_title(self, text: str, filename: str) -> str:
        """Extract paper title from text or use filename as fallback."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Look for title in first few lines, but skip journal headers and common patterns
        for i, line in enumerate(lines[:15]):  # Check more lines
            # Skip common patterns that are NOT titles
            skip_patterns = [
                'abstract', 'introduction', 'page', 'doi:', 'http', 'www.',
                'physical review', 'journal', 'vol', 'volume', 'issue',
                'published', 'received', 'accepted', 'arxiv:', 'preprint',
                'copyright', '©', 'license', 'rights reserved',
                'department', 'university', 'college', 'school',
                'email', '@', '.edu', '.com', '.org'
            ]
            
            # Check if line looks like a title
            if (10 < len(line) < 300 and  # Reasonable title length
                not any(pattern in line.lower() for pattern in skip_patterns) and
                not line.isupper() and  # Skip all-caps headers
                not line.replace(' ', '').replace(',', '').replace('(', '').replace(')', '').isdigit() and  # Skip page numbers
                not line.startswith('Fig') and  # Skip figure captions
                not line.startswith('Table') and  # Skip table captions
                line[0].isupper()):  # Title should start with capital letter
                
                # If this looks like a title, check if the next line continues it
                potential_title = line
                
                # Check if next lines continue the title (common with long titles)
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j]
                    # If next line looks like a continuation (starts lowercase or is short)
                    if (len(next_line) < 100 and 
                        not any(pattern in next_line.lower() for pattern in skip_patterns) and
                        not next_line[0].isupper() and next_line[0].isalpha() or
                        (len(next_line.split()) < 8 and not any(word in next_line.lower() for word in ['author', 'university', 'department']))):
                        potential_title += " " + next_line
                    else:
                        break
                
                return potential_title.strip()
        
        # Fallback to filename without extension
        return Path(filename).stem
    
    def _smart_text_processing(self, text: str) -> str:
        """Process text intelligently to fit within token limits while preserving key information."""
        # Rough estimation: 1 token ≈ 4 characters
        estimated_tokens = len(text) // 4
        
        if estimated_tokens <= MAX_CONTEXT_TOKENS:
            # Text fits comfortably, use as-is
            return text
        
        self.logger.info(f"Large text detected (~{estimated_tokens} tokens). Using smart extraction.")
        
        # Split into sections and prioritize important parts
        lines = text.split('\\n')
        sections = []
        current_section = []
        section_markers = ['abstract', 'introduction', 'method', 'result', 'discussion', 'conclusion', 'reference']
        
        # Group lines into sections
        current_header = "start"
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            is_header = False
            for marker in section_markers:
                if marker in line_lower and len(line_lower) < 50:
                    if current_section:
                        sections.append((current_header, '\\n'.join(current_section)))
                    current_section = [line]
                    current_header = marker
                    is_header = True
                    break
            
            if not is_header:
                current_section.append(line)
        
        # Don't forget the last section
        if current_section:
            sections.append((current_header, '\\n'.join(current_section)))
        
        # Prioritize sections for extraction
        priority_order = ['abstract', 'introduction', 'method', 'result', 'discussion', 'start']
        selected_text = ""
        
        # Add sections in priority order until we approach token limit
        for priority in priority_order:
            for header, content in sections:
                if header == priority:
                    potential_text = selected_text + "\\n\\n" + content
                    if len(potential_text) // 4 < MAX_CONTEXT_TOKENS * 0.8:  # Leave 20% buffer
                        selected_text = potential_text
                    else:
                        # If adding this section would exceed limit, add partial content
                        remaining_chars = int((MAX_CONTEXT_TOKENS * 4 * 0.8) - len(selected_text))
                        if remaining_chars > 1000:  # Only add if meaningful amount remains
                            selected_text += "\\n\\n" + content[:remaining_chars] + "\\n[SECTION TRUNCATED]"
                        self.logger.info(f"Reached token limit. Using {len(selected_text)} characters.")
                        return selected_text
        
        return selected_text if selected_text else text[:int(MAX_CONTEXT_TOKENS * 4)]  # Fallback
    
    def process_with_openai(self, paper_text: str, title: str) -> Dict[str, str]:
        """Process paper text with OpenAI to extract coding information."""
        try:
            # Use smart text processing for large documents
            processed_text = self._smart_text_processing(paper_text)
            
            # Prepare the prompt
            full_prompt = f"{self.prompt_template}\\n\\nRESEARCH PAPER:\\n{processed_text}"
            
            # Prepare completion parameters - handle different models
            completion_params = {
                "model": OPENAI_MODEL,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert researcher specializing in educational technology and learning sciences. Your task is to carefully analyze research papers and extract specific coding information for a systematic literature review."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            }
            
            # Use appropriate token parameter based on model
            if "gpt-5" in OPENAI_MODEL or "gpt-4o" in OPENAI_MODEL:
                completion_params["max_completion_tokens"] = OPENAI_MAX_TOKENS
            else:
                completion_params["max_tokens"] = OPENAI_MAX_TOKENS
            
            # Only set temperature if model supports it (gpt-5-mini only supports default temperature)
            if "gpt-5-mini" not in OPENAI_MODEL:
                completion_params["temperature"] = OPENAI_TEMPERATURE
            
            response = self.client.chat.completions.create(**completion_params)
            
            response_text = response.choices[0].message.content
            
            # Log the response for debugging
            self.logger.info(f"Received response length: {len(response_text) if response_text else 0}")
            if response_text and len(response_text) > 0:
                self.logger.info(f"Response preview: {response_text[:300]}...")
            else:
                self.logger.warning("Empty response received from OpenAI")
            
            # Parse the response into structured data
            coded_data = self._parse_openai_response(response_text, title)
            
            self.logger.info(f"Successfully processed paper: {title}")
            return coded_data
            
        except Exception as e:
            self.logger.error(f"Error processing with OpenAI: {e}")
            return self._create_empty_row(title)
    
    def _parse_openai_response(self, response_text: str, title: str) -> Dict[str, str]:
        """Parse OpenAI response into structured coding data."""
        # Initialize with default values
        coded_data = {col: "Not specified" for col in CSV_COLUMNS}
        coded_data['Title'] = title
        
        # If response is empty or too short, return defaults
        if not response_text or len(response_text.strip()) < 10:
            self.logger.warning(f"Empty or very short response received: '{response_text}'")
            return coded_data
        
        self.logger.info(f"Processing response of length: {len(response_text)}")
        
        try:
            # More precise parsing based on numbered questions
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            
            # Map question numbers/keywords to exact columns
            question_mapping = {
                '1': '1.1 Primary Stakeholders',
                'primary stakeholders': '1.1 Primary Stakeholders', 
                'stakeholders': '1.1 Primary Stakeholders',
                
                '2': '1.2 Context',
                'context': '1.2 Context',
                
                '3': '1.3 Tech/AI type', 
                'tech/ai type': '1.3 Tech/AI type',
                'technology': '1.3 Tech/AI type',
                
                '4': '1.4 Tool/Platform',
                'tool/platform': '1.4 Tool/Platform',
                'platform': '1.4 Tool/Platform',
                
                '5': '1.5 Education level',
                'education level': '1.5 Education level',
                
                '6': '2.1 Feedback term',
                'feedback term': '2.1 Feedback term',
                
                '7': '2.2 Description of context',
                'description of context': '2.2 Description of context',
                
                '8': '2.3 Our evaluation',
                'our evaluation': '2.3 Our evaluation',
                'evaluation': '2.3 Our evaluation',
                
                '9': '3.1 Agency type',
                'agency type': '3.1 Agency type',
                'agency': '3.1 Agency type',
                
                '10': '3.2 Feedback timing control',
                'feedback timing control': '3.2 Feedback timing control',
                'timing control': '3.2 Feedback timing control',
                'timing': '3.2 Feedback timing control',
                
                '11': '4.1 Metrics for evaluation',
                'metrics for evaluation': '4.1 Metrics for evaluation',
                'metrics': '4.1 Metrics for evaluation',
                
                '12': '4.2 Measurement of agency',
                'measurement of agency': '4.2 Measurement of agency',
                'measurement': '4.2 Measurement of agency'
            }
            
            # Process lines looking for numbered answers or keyword matches
            for i, line in enumerate(lines):
                line_lower = line.lower()
                matched_column = None
                answer = ""
                
                # Check for numbered format (e.g., "1. **Primary Stakeholders**: answer")
                for num in range(1, 13):
                    if line_lower.startswith(f"{num}."):
                        if str(num) in question_mapping:
                            matched_column = question_mapping[str(num)]
                            # Extract answer after colon or after the question
                            if ':' in line:
                                answer = line.split(':', 1)[1].strip()
                                # Remove markdown formatting
                                answer = answer.replace('**', '').replace('*', '').strip()
                            break
                
                # If no numbered match, check for keyword matches at start of line
                if not matched_column:
                    for keyword, column in question_mapping.items():
                        if keyword != str(keyword) and line_lower.startswith(keyword):
                            matched_column = column
                            if ':' in line:
                                answer = line.split(':', 1)[1].strip()
                                answer = answer.replace('**', '').replace('*', '').strip()
                            break
                
                # If we found a match, extract and clean the answer
                if matched_column and answer:
                    coded_data[matched_column] = answer
                    self.logger.info(f"Extracted {matched_column}: {answer[:50]}...")
                
                # Also check if this line contains an answer without explicit question marker
                elif ':' in line and len(line.split(':')) == 2:
                    question_part, answer_part = line.split(':', 1)
                    question_lower = question_part.lower().strip()
                    
                    # Try to match question part to our mapping
                    for keyword, column in question_mapping.items():
                        if keyword in question_lower:
                            answer_clean = answer_part.replace('**', '').replace('*', '').strip()
                            if answer_clean and coded_data[column] == "Not specified":
                                coded_data[column] = answer_clean
                                self.logger.info(f"Extracted {column}: {answer_clean[:50]}...")
                            break
            
            # Log extraction summary
            extracted_count = sum(1 for v in coded_data.values() if v != "Not specified" and v != title)
            self.logger.info(f"Successfully extracted {extracted_count} out of {len(CSV_COLUMNS)-1} fields")
            
        except Exception as e:
            self.logger.warning(f"Error parsing response: {e}")
            self.logger.warning(f"Response preview: {response_text[:200]}...")
        
        return coded_data
    
    def _create_empty_row(self, title: str) -> Dict[str, str]:
        """Create empty row with default values when processing fails."""
        return {col: "Processing failed" for col in CSV_COLUMNS if col != 'Title'} | {'Title': title}
    
    def process_all_pdfs(self) -> List[Dict[str, str]]:
        """Process all PDF files in the PDF folder."""
        pdf_folder = Path(PDF_FOLDER)
        
        if not pdf_folder.exists():
            self.logger.error(f"PDF folder {PDF_FOLDER} does not exist")
            return []
        
        pdf_files = list(pdf_folder.glob("*.pdf"))
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {PDF_FOLDER}")
            return []
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        results = []
        
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            self.logger.info(f"Processing: {pdf_file.name}")
            
            # Extract text
            text = self.extract_text_from_pdf(str(pdf_file))
            
            if not text:
                self.logger.warning(f"No text extracted from {pdf_file.name}")
                results.append(self._create_empty_row(pdf_file.name))
                continue
            
            # Get title
            title = self.get_paper_title(text, pdf_file.name)
            
            # Process with OpenAI
            coded_data = self.process_with_openai(text, title)
            results.append(coded_data)
        
        return results
    
    def save_to_csv(self, results: List[Dict[str, str]], filename: Optional[str] = None) -> str:
        """Save results to CSV file."""
        if not results:
            self.logger.warning("No results to save")
            return ""
        
        # Create output directory if it doesn't exist
        output_dir = Path(OUTPUT_FOLDER)
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"literature_coding_results_{timestamp}.csv"
        
        output_path = output_dir / filename
        
        try:
            # Save to CSV
            df = pd.DataFrame(results, columns=CSV_COLUMNS)
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            self.logger.info(f"Results saved to {output_path}")
            self.logger.info(f"Processed {len(results)} papers")
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            raise
    
    def run(self, output_filename: Optional[str] = None) -> str:
        """Main method to run the complete extraction process."""
        self.logger.info("Starting literature review extraction process")
        
        try:
            # Process all PDFs
            results = self.process_all_pdfs()
            
            if not results:
                self.logger.error("No results to save")
                return ""
            
            # Save to CSV
            output_path = self.save_to_csv(results, output_filename)
            
            self.logger.info("Literature review extraction completed successfully")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error in extraction process: {e}")
            raise


def main():
    """Main function to run the literature review extractor."""
    try:
        extractor = LiteratureReviewExtractor()
        output_path = extractor.run()
        
        if output_path:
            print(f"\n✅ Extraction completed successfully!")
            print(f"📊 Results saved to: {output_path}")
            print(f"📁 Check the '{OUTPUT_FOLDER}' folder for your CSV file")
        else:
            print("❌ Extraction failed - check logs for details")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your configuration and try again")


if __name__ == "__main__":
    main()