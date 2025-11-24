#!/usr/bin/env python3
"""
Test PDF extraction for all files in the pdfs folder.
This script verifies that text can be extracted from all PDF files
without running the full OpenAI processing pipeline.
"""

import logging
from pathlib import Path
from literature_review_extractor import LiteratureReviewExtractor


def test_all_pdf_extraction():
    """Test text extraction for all PDF files in the pdfs folder."""
    
    # Setup basic logging for this test
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings and errors
        format='%(levelname)s - %(message)s'
    )
    
    # Initialize extractor (without OpenAI connection needed)
    try:
        extractor = LiteratureReviewExtractor()
    except Exception as e:
        print(f"⚠️  Note: OpenAI initialization failed ({e}), but text extraction testing will continue")
        # Create a minimal extractor instance for testing
        extractor = type('MockExtractor', (), {})()
        extractor.logger = logging.getLogger(__name__)
        
        # Import the extraction method directly
        from literature_review_extractor import LiteratureReviewExtractor
        temp_extractor = LiteratureReviewExtractor.__new__(LiteratureReviewExtractor)
        extractor.extract_text_from_pdf = temp_extractor.extract_text_from_pdf.__get__(extractor)
    
    pdf_folder = Path("pdfs")
    
    if not pdf_folder.exists():
        print(f"❌ PDF folder '{pdf_folder}' does not exist")
        return False
    
    # Find all PDF files
    pdf_files = list(pdf_folder.glob("*.pdf")) + list(pdf_folder.glob("*.PDF"))
    pdf_files = list(set(pdf_files))  # Remove duplicates
    
    if not pdf_files:
        print(f"❌ No PDF files found in '{pdf_folder}'")
        return False
    
    print(f"🔍 Testing text extraction for {len(pdf_files)} PDF files")
    print("=" * 80)
    
    successful = 0
    failed = 0
    results = []
    
    for pdf_file in sorted(pdf_files):
        print(f"📄 Testing: {pdf_file.name}")
        
        try:
            # Get file size
            file_size = pdf_file.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            # Extract text
            text = extractor.extract_text_from_pdf(str(pdf_file))
            
            if text and len(text.strip()) > 0:
                char_count = len(text)
                word_count = len(text.split())
                
                print(f"   ✅ SUCCESS - {char_count:,} chars, {word_count:,} words, {size_mb:.1f}MB")
                
                # Show first 100 characters as preview
                preview = text[:100].replace('\n', ' ').strip()
                print(f"   📝 Preview: {preview}...")
                
                results.append({
                    'file': pdf_file.name,
                    'status': 'SUCCESS',
                    'chars': char_count,
                    'words': word_count,
                    'size_mb': size_mb
                })
                successful += 1
                
            else:
                print(f"   ❌ FAILED - No text extracted ({size_mb:.1f}MB)")
                results.append({
                    'file': pdf_file.name,
                    'status': 'FAILED',
                    'chars': 0,
                    'words': 0,
                    'size_mb': size_mb
                })
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR - {str(e)}")
            results.append({
                'file': pdf_file.name,
                'status': 'ERROR',
                'error': str(e)
            })
            failed += 1
            
        print()  # Empty line between files
    
    # Summary
    print("=" * 80)
    print(f"📊 EXTRACTION TEST SUMMARY")
    print(f"   Total files: {len(pdf_files)}")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success rate: {(successful/len(pdf_files)*100):.1f}%")
    
    if failed > 0:
        print(f"\n⚠️  FAILED FILES:")
        for result in results:
            if result['status'] != 'SUCCESS':
                print(f"   - {result['file']} ({result['status']})")
    else:
        print(f"\n🎉 All PDF files can be successfully processed!")
    
    # Optional: Show statistics for successful extractions
    if successful > 0:
        successful_results = [r for r in results if r['status'] == 'SUCCESS']
        total_chars = sum(r['chars'] for r in successful_results)
        avg_chars = total_chars / len(successful_results)
        
        print(f"\n📈 EXTRACTION STATISTICS:")
        print(f"   Average characters per file: {avg_chars:,.0f}")
        print(f"   Total characters extracted: {total_chars:,}")
    
    return failed == 0


def main():
    """Main function to run the extraction test."""
    print("🧪 PDF Text Extraction Test")
    print("Testing all PDF files for successful text extraction...")
    print()
    
    success = test_all_pdf_extraction()
    
    if success:
        print("\n✅ All PDF files passed extraction test!")
        print("🚀 Ready for full literature review processing")
    else:
        print("\n❌ Some PDF files failed extraction")
        print("🔧 Check the failed files and consider manual review")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())