#!/usr/bin/env python3
"""
Recovery script to reprocess only the failed papers with enhanced parsing
"""

import pandas as pd
import logging
from pathlib import Path
from literature_review_extractor import LiteratureReviewExtractor

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Read the existing CSV to identify failed papers
    csv_path = "output/literature_coding_results_20251124_145733.csv"
    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    
    # Identify papers that failed processing (have "Processing failed" in multiple columns)
    failed_mask = df.apply(lambda row: sum(row == "Processing failed") >= 5, axis=1)
    failed_papers = df[failed_mask]['Title'].tolist()
    
    # Also identify papers that returned questions instead of answers
    question_mask = df.apply(lambda row: any(
        isinstance(val, str) and val.startswith(("What ", "How ", "Who ", "When ", "Where ", "Why ")) 
        for val in row if val != "Processing failed"
    ), axis=1)
    question_papers = df[question_mask]['Title'].tolist()
    
    all_failed_papers = list(set(failed_papers + question_papers))
    
    logger.info(f"Found {len(failed_papers)} papers with processing failures")
    logger.info(f"Found {len(question_papers)} papers with question responses")
    logger.info(f"Total unique papers to reprocess: {len(all_failed_papers)}")
    
    if not all_failed_papers:
        logger.info("No failed papers found. All papers processed successfully!")
        return
    
    # Map titles back to PDF files
    pdfs_dir = Path("pdfs")
    pdf_files = list(pdfs_dir.glob("*.pdf"))
    
    papers_to_reprocess = []
    for title in all_failed_papers:
        # Try to find matching PDF file
        matching_pdfs = [pdf for pdf in pdf_files if Path(pdf).stem.replace('_', ' ').replace('-', ' ').lower() in title.lower() or title.lower() in Path(pdf).stem.replace('_', ' ').replace('-', ' ').lower()]
        
        if matching_pdfs:
            papers_to_reprocess.append(matching_pdfs[0])
            logger.info(f"Will reprocess: {matching_pdfs[0].name} -> {title}")
        else:
            logger.warning(f"Could not find PDF file for failed paper: {title}")
    
    if not papers_to_reprocess:
        logger.error("No PDF files found for failed papers")
        return
    
    logger.info(f"Reprocessing {len(papers_to_reprocess)} papers with enhanced parsing...")
    
    # Initialize extractor
    extractor = LiteratureReviewExtractor()
    
    # Reprocess the failed papers
    results = []
    for pdf_path in papers_to_reprocess:
        logger.info(f"Reprocessing: {pdf_path}")
        try:
            result = extractor.extract_literature_codes(str(pdf_path))
            results.append(result)
            
            # Update the original dataframe
            title = result['Title']
            matching_indices = df[df['Title'].str.contains(title, case=False, na=False)].index
            if len(matching_indices) > 0:
                idx = matching_indices[0]
                for col, value in result.items():
                    if col in df.columns:
                        df.loc[idx, col] = value
                        
            logger.info(f"Successfully reprocessed: {title}")
        except Exception as e:
            logger.error(f"Failed to reprocess {pdf_path}: {str(e)}")
    
    # Save updated results
    backup_path = "output/literature_extraction_results_backup.csv"
    df.to_csv(backup_path, index=False)
    logger.info(f"Backup saved to: {backup_path}")
    
    df.to_csv(csv_path, index=False)
    logger.info(f"Updated results saved to: {csv_path}")
    
    # Summary
    logger.info(f"Reprocessing complete!")
    logger.info(f"Successfully reprocessed: {len([r for r in results if r])}")
    logger.info(f"Failed to reprocess: {len(papers_to_reprocess) - len([r for r in results if r])}")

if __name__ == "__main__":
    main()