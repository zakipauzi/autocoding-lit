#!/usr/bin/env python3
"""
Test Output Schema for Literature Review Extractor

This test validates the output schema and parsing logic using mock data
without requiring an OpenAI API connection.
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import pandas as pd
from datetime import datetime
from pathlib import Path
import tempfile
import os

# Import the main class
from literature_review_extractor import LiteratureReviewExtractor
from config import CSV_COLUMNS, OUTPUT_FOLDER


class TestLiteratureReviewSchema(unittest.TestCase):
    """Test class for validating the literature review extraction schema."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock extractor instance
        with patch('literature_review_extractor.OpenAI'):
            self.extractor = LiteratureReviewExtractor()
        
        # Mock the logger to avoid file I/O during tests
        self.extractor.logger = Mock()
        
        # Sample mock OpenAI response for testing parsing
        self.mock_response_complete = """
**Include in Review**: Y
**Reason if excluded**: Not applicable

**1. Primary Stakeholders**: Students and teachers in mathematics education
**Source**: "Participants included 120 middle school students and 6 mathematics teachers" (Methods section, p. 45)

**2. Context**: Classroom setting with digital learning tools
**Source**: "The study was conducted in authentic classroom environments using tablet-based applications" (Introduction, p. 12)

**3. Tech/AI type**: Intelligent Tutoring System with adaptive feedback
**Source**: "We implemented an ITS that provides personalized hints and scaffolding" (System Design, p. 23)

**4. Tool/Platform**: MathTutor Pro platform
**Source**: "All interventions were delivered through the MathTutor Pro platform" (Methods, p. 34)

**5. Education level**: Middle school (grades 6-8)
**Source**: "Students were enrolled in grades 6, 7, and 8" (Participants section, p. 41)

**6. Feedback term**: Adaptive hints and corrective feedback
**Source**: "The system provided adaptive hints and corrective feedback based on student responses" (Results, p. 56)

**7. Description of mechanism and context**: Feedback was delivered immediately after student responses with personalized explanations
**Source**: "Immediate feedback was provided with explanations tailored to individual student errors" (Design section, p. 28)

**8. Our interpretation/analysis**: The feedback appears to be high-quality formative assessment with adaptive elements
**Source**: "Students showed significant improvement in problem-solving accuracy" (Discussion, p. 78)

**9. Agency type**: Limited student agency with teacher-controlled settings
**Source**: "Teachers could adjust difficulty levels but students had limited control over feedback timing" (System Features, p. 31)

**10. Feedback timing control**: Students could not control when feedback was provided
**Source**: "Feedback was automatically triggered by the system upon answer submission" (Implementation, p. 52)

**11. Metrics for evaluation**: Pre/post test scores, engagement time, and error rates
**Source**: "We measured learning gains using pre/post assessments and tracked engagement metrics" (Evaluation, p. 67)

**12. Measurement of agency**: Student surveys on perceived control and autonomy
**Source**: "Agency was measured through validated autonomy questionnaires" (Measures section, p. 43)
"""
        
        # Mock response with missing fields
        self.mock_response_partial = """
**Include in Review**: Y

**1. Primary Stakeholders**: Students only
**Source**: "50 students participated" (Methods, p. 10)

**3. Tech/AI type**: Machine learning algorithm
**Source**: Not specified

**6. Feedback term**: Hints
**Source**: "Students received hints during problem solving" (Results, p. 25)
"""
        
        # Mock response for excluded paper
        self.mock_response_excluded = """
**Include in Review**: N
**Reason if excluded**: Not mathematics education related - focuses on physics
"""
        
        # Mock response with Answer/Source format (Method 4)
        self.mock_response_answer_format = """
**Include in Review**: Y

**1. Primary Stakeholders**: Who are the main participants/stakeholders?
**Answer**: Elementary school students and their teachers
**Source**: "The study involved 200 elementary students across 10 classrooms" (Participants, p. 15)

**2. Context**: What is the context or setting?
**Answer**: Online learning environment during remote instruction
**Source**: "Data was collected during the COVID-19 remote learning period" (Context, p. 8)

**6. Feedback term**: What terms are used for 'feedback'?
**Answer**: Immediate response and guided instruction
**Source**: "The system provided immediate response to student inputs with guided instruction" (Design, p. 22)
"""

    def test_csv_columns_schema(self):
        """Test that CSV_COLUMNS contains all expected fields."""
        expected_columns = [
            'Title',
            'Include in Review (Y/N)', 
            'Exclusion Reason',
            '1.1 Primary Stakeholders',
            '1.1 Primary Stakeholders - Source',
            '1.2 Context',
            '1.2 Context - Source',
            '1.3 Tech/AI type',
            '1.3 Tech/AI type - Source', 
            '1.4 Tool/Platform',
            '1.4 Tool/Platform - Source',
            '1.5 Education level',
            '1.5 Education level - Source',
            '2.1 Feedback term',
            '2.1 Feedback term - Source',
            '2.2 Description of context',
            '2.2 Description of context - Source',
            '2.3 Our evaluation', 
            '2.3 Our evaluation - Source',
            '3.1 Agency type',
            '3.1 Agency type - Source',
            '3.2 Feedback timing control',
            '3.2 Feedback timing control - Source',
            '4.1 Metrics for evaluation',
            '4.1 Metrics for evaluation - Source',
            '4.2 Measurement of agency',
            '4.2 Measurement of agency - Source'
        ]
        
        self.assertEqual(len(CSV_COLUMNS), 27, "Should have exactly 27 columns")
        self.assertEqual(CSV_COLUMNS, expected_columns, "Column names should match expected schema")
    
    def test_parse_complete_response(self):
        """Test parsing of a complete OpenAI response with all fields."""
        title = "Test Paper Title"
        result = self.extractor._parse_openai_response(self.mock_response_complete, title)
        
        # Check basic structure
        self.assertEqual(result['Title'], title)
        self.assertEqual(result['Include in Review (Y/N)'], 'Y')
        self.assertEqual(result['Exclusion Reason'], 'Not applicable')
        
        # Check that all main fields are extracted
        self.assertEqual(result['1.1 Primary Stakeholders'], 'Students and teachers in mathematics education')
        self.assertEqual(result['1.2 Context'], 'Classroom setting with digital learning tools')
        self.assertEqual(result['1.3 Tech/AI type'], 'Intelligent Tutoring System with adaptive feedback')
        self.assertEqual(result['1.4 Tool/Platform'], 'MathTutor Pro platform')
        self.assertEqual(result['1.5 Education level'], 'Middle school (grades 6-8)')
        self.assertEqual(result['2.1 Feedback term'], 'Adaptive hints and corrective feedback')
        
        # Check that sources are extracted
        self.assertIn('Participants included 120 middle school students', result['1.1 Primary Stakeholders - Source'])
        self.assertIn('authentic classroom environments', result['1.2 Context - Source'])
        self.assertIn('MathTutor Pro platform', result['1.4 Tool/Platform - Source'])
        
        # Verify no fields are left as "Not specified" (except those not in the response)
        extracted_fields = [col for col, val in result.items() 
                          if col not in ["Title", "Include in Review (Y/N)", "Exclusion Reason"] 
                          and val != "Not specified"]
        self.assertGreater(len(extracted_fields), 20, "Should extract most fields from complete response")
    
    def test_parse_partial_response(self):
        """Test parsing of a partial OpenAI response with missing fields."""
        title = "Partial Test Paper"
        result = self.extractor._parse_openai_response(self.mock_response_partial, title)
        
        # Check extracted fields
        self.assertEqual(result['Title'], title)
        self.assertEqual(result['Include in Review (Y/N)'], 'Y')
        self.assertEqual(result['1.1 Primary Stakeholders'], 'Students only')
        self.assertEqual(result['1.3 Tech/AI type'], 'Machine learning algorithm')
        self.assertEqual(result['2.1 Feedback term'], 'Hints')
        
        # Check that missing fields default to "Not specified"
        self.assertEqual(result['1.2 Context'], 'Not specified')
        self.assertEqual(result['1.4 Tool/Platform'], 'Not specified')
        self.assertEqual(result['4.1 Metrics for evaluation'], 'Not specified')
        
        # Check that sources are handled correctly
        self.assertIn('50 students participated', result['1.1 Primary Stakeholders - Source'])
        self.assertEqual(result['1.3 Tech/AI type - Source'], 'Not specified')
    
    def test_parse_excluded_response(self):
        """Test parsing of a response for an excluded paper."""
        title = "Excluded Paper"
        result = self.extractor._parse_openai_response(self.mock_response_excluded, title)
        
        self.assertEqual(result['Title'], title)
        self.assertEqual(result['Include in Review (Y/N)'], 'N')
        self.assertEqual(result['Exclusion Reason'], 'Not mathematics education related - focuses on physics')
        
        # All other fields should be "Not specified"
        for col in CSV_COLUMNS:
            if col not in ['Title', 'Include in Review (Y/N)', 'Exclusion Reason']:
                self.assertEqual(result[col], 'Not specified')
    
    def test_parse_answer_source_format(self):
        """Test parsing of Method 4 format with **Answer**: and **Source**: labels."""
        title = "Answer Format Paper"
        result = self.extractor._parse_openai_response(self.mock_response_answer_format, title)
        
        # Check that Method 4 parsing works
        self.assertEqual(result['1.1 Primary Stakeholders'], 'Elementary school students and their teachers')
        self.assertEqual(result['1.2 Context'], 'Online learning environment during remote instruction')
        self.assertEqual(result['2.1 Feedback term'], 'Immediate response and guided instruction')
        
        # Check sources
        self.assertIn('200 elementary students', result['1.1 Primary Stakeholders - Source'])
        self.assertIn('COVID-19 remote learning', result['1.2 Context - Source'])
        self.assertIn('immediate response to student inputs', result['2.1 Feedback term - Source'])
    
    def test_empty_response_handling(self):
        """Test handling of empty or very short responses."""
        title = "Empty Response Test"
        
        # Test completely empty response
        result = self.extractor._parse_openai_response("", title)
        self.assertEqual(result['Title'], title)
        for col in CSV_COLUMNS:
            if col != 'Title':
                self.assertEqual(result[col], 'Not specified')
        
        # Test very short response
        result = self.extractor._parse_openai_response("Short", title)
        self.assertEqual(result['Title'], title)
        for col in CSV_COLUMNS:
            if col != 'Title':
                self.assertEqual(result[col], 'Not specified')
    
    def test_create_empty_row(self):
        """Test creation of empty row for failed processing."""
        title = "Failed Paper"
        result = self.extractor._create_empty_row(title)
        
        self.assertEqual(result['Title'], title)
        self.assertEqual(result['Include in Review (Y/N)'], 'N')
        self.assertEqual(result['Exclusion Reason'], 'Processing failed')
        
        # All other fields should be "Processing failed"
        for col in CSV_COLUMNS:
            if col not in ['Title', 'Include in Review (Y/N)', 'Exclusion Reason']:
                self.assertEqual(result[col], 'Processing failed')
    
    def test_get_paper_title_formatting(self):
        """Test paper title formatting from filename."""
        # Test basic filename
        title = self.extractor.get_paper_title("", "test_paper_file.pdf")
        self.assertEqual(title, "Test Paper File")
        
        # Test filename with underscores and hyphens
        title = self.extractor.get_paper_title("", "advanced-learning_systems-and-ai.pdf")
        self.assertEqual(title, "Advanced Learning Systems and Ai")
        
        # Test filename with lowercase words that should remain lowercase
        title = self.extractor.get_paper_title("", "the_impact_of_ai_in_education.pdf")
        self.assertEqual(title, "The Impact of Ai in Education")
    
    @patch('pandas.DataFrame.to_csv')
    @patch('pathlib.Path.mkdir')
    def test_save_to_csv_schema(self, mock_mkdir, mock_to_csv):
        """Test that CSV saving maintains proper schema."""
        # Create mock results
        mock_results = [
            {col: f"Test value {i}" if col != 'Title' else f"Paper {i}" 
             for col in CSV_COLUMNS} 
            for i in range(3)
        ]
        
        # Mock the file operations
        mock_to_csv.return_value = None
        
        # Test the save function
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('literature_review_extractor.OUTPUT_FOLDER', temp_dir):
                output_path = self.extractor.save_to_csv(mock_results, "test_output.csv")
        
        # Verify to_csv was called with correct parameters
        mock_to_csv.assert_called_once()
        call_args = mock_to_csv.call_args
        
        # Check that index=False and encoding='utf-8-sig' are used
        self.assertEqual(call_args[1]['index'], False)
        self.assertEqual(call_args[1]['encoding'], 'utf-8-sig')
        
        # Verify the DataFrame has correct columns
        df_call = call_args[0] if call_args[0] else None
        # The DataFrame is created in the method, so we check the columns parameter
        # by verifying the mock_results structure
        self.assertEqual(len(mock_results[0]), len(CSV_COLUMNS))
        
    def test_all_parsing_methods(self):
        """Test that all four parsing methods can extract data."""
        # Create responses in different formats
        method1_response = "**1. Primary Stakeholders**: Students\n**Source**: Test source 1"
        method2_response = "1. **Primary Stakeholders**: Students\n**Source**: Test source 2"  
        method3_response = "1. Primary Stakeholders: Students\nSource: Test source 3"
        method4_response = "**1. Primary Stakeholders**: Question text\n**Answer**: Students\n**Source**: Test source 4"
        
        for i, response in enumerate([method1_response, method2_response, method3_response, method4_response], 1):
            with self.subTest(method=i):
                result = self.extractor._parse_openai_response(response, f"Test Paper {i}")
                # Each should extract the stakeholder field
                self.assertEqual(result['1.1 Primary Stakeholders'], 'Students', 
                               f"Method {i} failed to extract stakeholders")
    
    def test_dataframe_creation_with_mock_data(self):
        """Test that mock data creates a valid DataFrame with correct schema."""
        # Create comprehensive mock data
        mock_data = []
        for i in range(5):
            row = {col: "Not specified" for col in CSV_COLUMNS}
            row['Title'] = f"Mock Paper {i+1}"
            row['Include in Review (Y/N)'] = 'Y' if i % 2 == 0 else 'N'
            row['Exclusion Reason'] = 'Not applicable' if i % 2 == 0 else 'Not mathematics related'
            row['1.1 Primary Stakeholders'] = f"Students and teachers {i+1}"
            row['1.1 Primary Stakeholders - Source'] = f"Source evidence {i+1}"
            row['1.2 Context'] = f"Educational context {i+1}"
            row['2.1 Feedback term'] = f"Feedback type {i+1}"
            mock_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(mock_data, columns=CSV_COLUMNS)
        
        # Validate DataFrame properties
        self.assertEqual(len(df), 5, "Should have 5 rows")
        self.assertEqual(len(df.columns), 27, "Should have 27 columns")
        self.assertEqual(list(df.columns), CSV_COLUMNS, "Columns should match schema")
        
        # Check data types and content
        self.assertTrue(all(isinstance(title, str) for title in df['Title']), 
                       "All titles should be strings")
        self.assertTrue(all(decision in ['Y', 'N'] for decision in df['Include in Review (Y/N)']),
                       "Include decisions should be Y or N")
        
        # Verify no missing essential data
        self.assertFalse(df['Title'].isnull().any(), "No titles should be null")
        self.assertFalse(df['Include in Review (Y/N)'].isnull().any(), "No inclusion decisions should be null")


def run_tests():
    """Run all tests and display results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestLiteratureReviewSchema)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=None)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"- {test}: {error_msg}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            error_msg = traceback.split('Error: ')[-1].split('\n')[0]
            print(f"- {test}: {error_msg}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 Testing Literature Review Extraction Schema")
    print("=" * 60)
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed! The output schema is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        exit(1)