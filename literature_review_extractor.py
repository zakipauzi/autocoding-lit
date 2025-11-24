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
import unicodedata
import re
try:
    import fitz  # PyMuPDF - for additional text extraction
except ImportError:
    fitz = None

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
        """Extract text from PDF with multiple fallback methods."""
        # Method 1: Standard pdfplumber
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            # Normalize Unicode characters
                            page_text = unicodedata.normalize('NFKD', page_text)
                            # Handle encoding issues
                            page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                            text += page_text + "\n"
                    except Exception as e:
                        self.logger.warning(f"Error extracting page {page_num + 1} from {pdf_path}: {str(e)}")
                        continue
            
            if text.strip():
                self.logger.info(f"Extracted {len(text)} characters from {pdf_path}")
                return text.strip()
        except Exception as e:
            self.logger.warning(f"Method 1 (pdfplumber standard) failed for {pdf_path}: {str(e)}")
        
        # Method 2: pdfplumber with tolerance settings
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                        if page_text:
                            page_text = unicodedata.normalize('NFKD', page_text)
                            page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                            text += page_text + "\n"
                    except Exception:
                        continue
            
            if text.strip():
                self.logger.info(f"Method 2 (pdfplumber tolerant) succeeded: {len(text)} characters from {pdf_path}")
                return text.strip()
        except Exception as e:
            self.logger.warning(f"Method 2 (pdfplumber tolerant) failed for {pdf_path}: {str(e)}")
        
        # Method 3: PyMuPDF (if available)
        if fitz:
            try:
                doc = fitz.open(pdf_path)
                text = ""
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        page_text = unicodedata.normalize('NFKD', page_text)
                        page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                        text += page_text + "\n"
                doc.close()
                
                if text.strip():
                    self.logger.info(f"Method 3 (PyMuPDF) succeeded: {len(text)} characters from {pdf_path}")
                    return text.strip()
            except Exception as e:
                self.logger.warning(f"Method 3 (PyMuPDF) failed for {pdf_path}: {str(e)}")
        
        self.logger.error(f"All text extraction methods failed for {pdf_path}")
        return ""
    
    def get_paper_title(self, text: str, filename: str) -> str:
        """Use filename as paper title with proper formatting."""
        # Use filename without extension as title
        title = Path(filename).stem
        
        # Clean up the filename to make it more readable
        # Replace common separators with spaces
        title = title.replace('_', ' ').replace('-', ' ')
        
        # Handle multiple spaces
        title = ' '.join(title.split())
        
        # Ensure proper capitalization (title case)
        # Keep certain words lowercase unless they start the title
        lowercase_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'of', 'on', 'or', 'the', 'to', 'up', 'via', 'with'}
        words = title.split()
        
        # Capitalize first word and words not in lowercase_words list
        formatted_words = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                formatted_words.append(word.capitalize())
            else:
                formatted_words.append(word.lower())
        
        formatted_title = ' '.join(formatted_words)
        
        self.logger.info(f"Using filename as title: {formatted_title}")
        return formatted_title
    
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
        """Parse OpenAI response into structured coding data with source evidence."""
        # Initialize with default values
        coded_data = {col: "Not specified" for col in CSV_COLUMNS}
        coded_data['Title'] = title
        
        # If response is empty or too short, return defaults
        if not response_text or len(response_text.strip()) < 10:
            self.logger.warning(f"Empty or very short response received: '{response_text}'")
            return coded_data
        
        self.logger.info(f"Processing response of length: {len(response_text)}")
        
        try:
            # Split response into lines for processing
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            
            # First, look for inclusion/exclusion decision and reason
            for line in lines:
                if line.startswith("**Include in Review**:"):
                    include_decision = line.replace("**Include in Review**:", "").strip()
                    coded_data['Include in Review (Y/N)'] = include_decision
                    self.logger.info(f"Extracted inclusion decision: {include_decision}")
                elif line.startswith("**Reason if excluded**:"):
                    exclusion_reason = line.replace("**Reason if excluded**:", "").strip()
                    coded_data['Exclusion Reason'] = exclusion_reason
                    self.logger.info(f"Extracted exclusion reason: {exclusion_reason}")
            
            # Base column names (without " - Source" suffix)
            base_columns = {
                '1': '1.1 Primary Stakeholders',
                '2': '1.2 Context',
                '3': '1.3 Tech/AI type', 
                '4': '1.4 Tool/Platform',
                '5': '1.5 Education level',
                '6': '2.1 Feedback term',
                '7': '2.2 Description of context',
                '8': '2.3 Our evaluation',
                '9': '3.1 Agency type',
                '10': '3.2 Feedback timing control',
                '11': '4.1 Metrics for evaluation',
                '12': '4.2 Measurement of agency'
            }
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Method 1: Look for format "**X. [Question Title]**: content"
                for num_str, base_column in base_columns.items():
                    if line.startswith(f"**{num_str}."):
                        # Extract everything after the first colon
                        if ":" in line:
                            answer = line.split(":", 1)[1].strip()
                            # Remove any additional ** formatting
                            answer = answer.replace("**", "").strip()
                            
                            # Filter out questions (shouldn't start with question words)
                            question_starters = ["what ", "how ", "who ", "when ", "where ", "why ", "does ", "do ", "is ", "are ", "can ", "will ", "should "]
                            if not any(answer.lower().startswith(q) for q in question_starters) and len(answer) > 3:
                                coded_data[base_column] = answer
                                self.logger.info(f"Method 1 - Extracted {base_column}: {answer[:50]}...")
                                
                                # Look for source in next few lines
                                source_column = base_column + " - Source"
                                j = i + 1
                                while j < len(lines) and j < i + 5:
                                    next_line = lines[j]
                                    if next_line.startswith("**Source**:"):
                                        source = next_line.replace("**Source**:", "").strip()
                                        coded_data[source_column] = source
                                        self.logger.info(f"Method 1 - Extracted {source_column}: {source[:50]}...")
                                        break
                                    elif any(next_line.startswith(f"**{n}.") for n in base_columns.keys()):
                                        break
                                    j += 1
                        break
                
                # Method 2: Look for format "X. **Field**: content" 
                for num_str, base_column in base_columns.items():
                    if line.startswith(f"{num_str}.") and "**:" in line:
                        answer_part = line.split("**:", 1)
                        if len(answer_part) > 1:
                            answer = answer_part[1].strip()
                            coded_data[base_column] = answer
                            self.logger.info(f"Extracted {base_column}: {answer[:50]}...")
                        break
                
                # Method 3: Look for simple numbered format "X. content"
                for num_str, base_column in base_columns.items():
                    # Skip if already extracted
                    if coded_data[base_column] != "Not specified":
                        continue
                        
                    if line.startswith(f"{num_str}.") and ":" in line:
                        answer = line.split(":", 1)[1].strip()
                        # Clean up markdown formatting
                        answer = answer.replace("**", "").replace("*", "").strip()
                        
                        # Enhanced question filtering
                        question_starters = ["what ", "how ", "who ", "when ", "where ", "why ", "does ", "do ", "is ", "are ", "can ", "will ", "should "]
                        if answer and not any(answer.lower().startswith(q) for q in question_starters) and len(answer) > 3:
                            coded_data[base_column] = answer
                            self.logger.info(f"Method 3 - Extracted {base_column}: {answer[:50]}...")
                            
                            # Look for source on next line for this method too
                            source_column = base_column + " - Source"
                            if i + 1 < len(lines):
                                next_line = lines[i + 1]
                                if "source" in next_line.lower() and ":" in next_line:
                                    source = next_line.split(":", 1)[1].strip()
                                    coded_data[source_column] = source
                                    self.logger.info(f"Method 3 - Extracted {source_column}: {source[:50]}...")
                        break
                
                i += 1            # Log extraction summary
            # Total fields = CSV_COLUMNS - 2 (exclude Title and Include columns) 
            total_fields = len(CSV_COLUMNS) - 2  
            extracted_count = sum(1 for col, val in coded_data.items() 
                                if col not in ["Title", "Include in Review (Y/N)", "Exclusion Reason"] and val != "Not specified")
            self.logger.info(f"Successfully extracted {extracted_count} out of {total_fields} fields")
            
        except Exception as e:
            self.logger.warning(f"Error parsing response: {e}")
            self.logger.warning(f"Response preview: {response_text[:300]}...")
        
        return coded_data
    
    def _create_empty_row(self, title: str) -> Dict[str, str]:
        """Create empty row with default values when processing fails."""
        empty_row = {col: "Processing failed" for col in CSV_COLUMNS if col not in ['Title', 'Include in Review (Y/N)', 'Exclusion Reason']}
        empty_row['Title'] = title
        empty_row['Include in Review (Y/N)'] = "N"  # Default to exclude if processing failed
        empty_row['Exclusion Reason'] = "Processing failed"
        return empty_row
    
    def process_all_pdfs(self) -> List[Dict[str, str]]:
        """Process all PDF files in the PDF folder."""
        pdf_folder = Path(PDF_FOLDER)
        
        if not pdf_folder.exists():
            self.logger.error(f"PDF folder {PDF_FOLDER} does not exist")
            return []
        
        # Find PDF files with both .pdf and .PDF extensions
        pdf_files = list(pdf_folder.glob("*.pdf")) + list(pdf_folder.glob("*.PDF"))
        
        # Remove duplicates (in case same file exists with different cases)
        pdf_files = list(set(pdf_files))
        
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
            # Save to CSV with better encoding handling
            df = pd.DataFrame(results, columns=CSV_COLUMNS)
            
            # Ensure all text data is properly encoded
            for col in df.columns:
                if df[col].dtype == 'object':  # Text columns
                    df[col] = df[col].astype(str).apply(
                        lambda x: x.encode('utf-8', errors='ignore').decode('utf-8') if isinstance(x, str) else x
                    )
            
            # Save with UTF-8 encoding and BOM for Excel compatibility
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
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