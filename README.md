# Literature Review AI Coding Tool

An automated tool for extracting structured coding information from research papers using OpenAI's API. This tool processes PDF files containing academic papers and extracts specific information needed for systematic literature reviews in educational technology and learning sciences.

## 🚀 Features

- **Automated PDF Processing**: Extract text from multiple PDF files in batch
- **AI-Powered Analysis**: Uses OpenAI GPT models to analyze research papers
- **Structured Data Extraction**: Extracts specific coding categories for literature reviews
- **CSV Output**: Generates structured CSV files with all extracted data
- **Configurable Prompts**: Customizable prompt templates for different review types
- **Robust Error Handling**: Comprehensive logging and error management
- **Progress Tracking**: Visual progress bars for batch processing

## 📁 Project Structure

```
autocoding-lit/
├── pdfs/                           # Place your PDF files here
├── output/                         # Generated CSV files
├── literature_review_extractor.py  # Main processing script
├── config.py                       # Configuration settings
├── prompt_template.txt             # AI prompt template
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## 🎯 Coding Schema

The tool extracts the following information categories:

### 1. Stakeholders & Context
- **1.1 Primary Stakeholders**: Who is involved in the study
- **1.2 Context**: Domain knowledge, educational setting, or tool context
- **1.3 Tech/AI type**: Type of technology or AI used
- **1.4 Tool/Platform**: Specific tools or platforms mentioned
- **1.5 Education level**: Educational level of participants

### 2. Feedback Analysis
- **2.1 Feedback term**: Lexical terms used for 'feedback'
- **2.2 Description of context**: How feedback context is described
- **2.3 Our evaluation**: Quality/type evaluation of feedback

### 3. Agency Analysis
- **3.1 Agency type**: Type of student/participant agency
- **3.2 Feedback timing control**: Student control over feedback timing

### 4. Measurement & Evaluation
- **4.1 Metrics for evaluation**: Metrics used to evaluate results
- **4.2 Measurement of agency**: How agency is measured

## 🛠 Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- OpenAI API key

### 2. Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

### 3. Configuration

You can modify settings in `config.py`:
- `OPENAI_MODEL`: Choose the OpenAI model (default: gpt-4o)
- `OPENAI_MAX_TOKENS`: Maximum tokens for response (default: 2000)
- `OPENAI_TEMPERATURE`: Response creativity (default: 0.3)
- `MAX_TEXT_LENGTH`: Maximum PDF text length (default: 50000)

## 📖 Usage

### 1. Prepare Your PDFs

Place all your research paper PDFs in the `pdfs/` folder.

### 2. Customize the Prompt (Optional)

Edit `prompt_template.txt` to modify the questions asked to the AI model. The default template includes questions for all coding categories.

### 3. Run the Extraction

Execute the main script:

```bash
python literature_review_extractor.py
```

### 4. View Results

- Results are saved as CSV files in the `output/` folder
- Each run creates a timestamped file (e.g., `literature_coding_results_20241120_143000.csv`)
- Open the CSV file in Excel, Google Sheets, or any spreadsheet application

## 📊 Output Format

The generated CSV file contains:
- **Title**: Extracted paper title or filename
- **All coding categories**: As defined in the coding schema above
- **Error handling**: "Not specified" for missing information, "Processing failed" for errors

## 🔧 Advanced Usage

### Custom Prompt Templates

You can create different prompt templates for different types of reviews:

1. Copy `prompt_template.txt` to a new file (e.g., `custom_prompt.txt`)
2. Modify the questions as needed
3. Update `PROMPT_FILE` in `config.py` to point to your custom template

### Processing Specific Files

To process only specific PDFs, you can modify the script or move unwanted PDFs out of the `pdfs/` folder temporarily.

### API Cost Management

- The tool uses OpenAI's API, which has usage costs
- Monitor your usage in the OpenAI dashboard
- Consider using `gpt-3.5-turbo` instead of `gpt-4o` for cost savings (update in `config.py`)

## 🔍 Troubleshooting

### Common Issues

1. **"OpenAI API key not found"**
   - Ensure your `.env` file exists and contains `OPENAI_API_KEY=your_key`
   - Verify the API key is valid in your OpenAI account

2. **"No PDF files found"**
   - Ensure PDF files are in the `pdfs/` folder
   - Check file extensions are `.pdf` (lowercase)

3. **"Processing failed" in results**
   - Check the log file `literature_extraction.log` for detailed errors
   - Verify PDF files are not corrupted or password-protected

4. **Poor extraction quality**
   - Adjust `OPENAI_TEMPERATURE` in `config.py` (lower = more consistent)
   - Modify the prompt template to be more specific
   - Try a different OpenAI model

### Logs

The tool generates detailed logs in `literature_extraction.log` which can help diagnose issues.

## 📝 Example Prompt Questions

The default prompt includes questions like:
- "Who are the primary stakeholders involved in this study?"
- "What is the context of this study?"
- "What lexical term was used to denote 'feedback'?"
- "Do students have any control over the timing of feedback?"
- "What metric(s) are used to evaluate the results?"

## 🤝 Contributing

Feel free to modify and extend this tool for your specific research needs. Common customizations include:
- Adding new coding categories
- Modifying the prompt template
- Changing output formats
- Adding data validation rules

## 📜 License

This project is licensed under the terms specified in the LICENSE file.

## ⚠️ Disclaimer

This tool uses AI to extract information from research papers. Always review and validate the extracted data before using it in your research. The quality of extraction depends on the clarity of the source papers and the effectiveness of the prompt template.