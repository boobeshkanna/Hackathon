"""
Project Setup Script
Creates the directory structure and initial files for the Vernacular Artisan Catalog project.
"""

import os
from pathlib import Path

def create_directory_structure():
    """Create the project directory structure."""
    
    directories = [
        "backend/lambda_functions/api_handlers",
        "backend/lambda_functions/orchestrator",
        "backend/lambda_functions/shared",
        "backend/models",
        "backend/services/sagemaker_client",
        "backend/services/bedrock_client",
        "backend/services/ondc_gateway",
        "backend/services/media_processing",
        "backend/infrastructure/cdk",
        "mobile",
        "tests/unit",
        "tests/property",
        "tests/integration",
        "docs",
        "scripts",
    ]
    
    print("Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Create __init__.py for Python packages
        if directory.startswith("backend/"):
            init_file = Path(directory) / "__init__.py"
            init_file.touch()
        print(f"✓ Created {directory}")
    
    print("\n✅ Directory structure created successfully!")

def create_init_files():
    """Create __init__.py files to make directories Python packages."""
    
    python_dirs = [
        "backend",
        "backend/lambda_functions",
        "backend/models",
        "backend/services",
        "tests",
    ]
    
    print("\nCreating __init__.py files...")
    for directory in python_dirs:
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f"✓ Created {init_file}")

if __name__ == "__main__":
    print("=" * 60)
    print("Vernacular Artisan Catalog - Project Setup")
    print("=" * 60)
    print()
    
    create_directory_structure()
    create_init_files()
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Create virtual environment: python -m venv venv")
    print("2. Activate it: source venv/bin/activate")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Copy .env.example to .env and fill in your values")
    print("5. Configure AWS CLI: aws configure")
    print()
