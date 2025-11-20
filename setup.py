#!/usr/bin/env python3
"""
Setup script for Literature Review AI Coding Tool
Helps users set up the environment and verify installation
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'openai', 'PyPDF2', 'python-dotenv', 
        'pandas', 'tqdm', 'pdfplumber'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    return missing_packages

def setup_environment():
    """Set up the environment file if it doesn't exist."""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        # Copy example to .env
        with open(env_example, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file and add your OpenAI API key")
        return True
    else:
        print("❌ .env.example file not found")
        return False

def check_folders():
    """Check if required folders exist."""
    folders = ['pdfs', 'output']
    
    for folder in folders:
        folder_path = Path(folder)
        if folder_path.exists():
            print(f"✅ {folder}/ folder exists")
        else:
            folder_path.mkdir(exist_ok=True)
            print(f"✅ Created {folder}/ folder")

def main():
    """Main setup function."""
    print("🔧 Literature Review AI Coding Tool Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return
    
    print("\n📦 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Install them with: pip install -r requirements.txt")
        return
    else:
        print("\n✅ All dependencies are installed")
    
    print("\n📁 Setting up folders...")
    check_folders()
    
    print("\n🔑 Setting up environment...")
    setup_environment()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Add your OpenAI API key to the .env file")
    print("2. Place PDF files in the pdfs/ folder")
    print("3. Run: python literature_review_extractor.py")

if __name__ == "__main__":
    main()