#!/usr/bin/env python3
"""
Setup script for enhanced SingleCellX pipeline.

Handles:
- Dependencies installation
- Database initialization
- Configuration validation
- Development/production setup
"""

import sys
import os
import subprocess
from pathlib import Path
import json
from datetime import datetime


def print_header(text):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    """Print success message."""
    print(f"✅ {text}")


def print_warning(text):
    """Print warning message."""
    print(f"⚠️  {text}")


def print_error(text):
    """Print error message."""
    print(f"❌ {text}")


def check_python_version():
    """Verify Python version >= 3.10."""
    print_header("Checking Python Version")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print_error(f"Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies(requirements_file="backend/requirements.txt"):
    """Install Python dependencies."""
    print_header("Installing Dependencies")
    
    if not Path(requirements_file).exists():
        print_error(f"Requirements file not found: {requirements_file}")
        return False
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True,
        )
        print_success("Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def setup_directories():
    """Create necessary directories."""
    print_header("Setting Up Directories")
    
    dirs = [
        Path("backend/uploads"),
        Path("backend/storage"),
        Path("backend/app/__pycache__"),
        Path("backend/app/services/__pycache__"),
        Path("backend/app/routes/__pycache__"),
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print_success(f"Created {d}")
    
    return True


def init_database():
    """Initialize the database."""
    print_header("Initializing Database")
    
    try:
        from backend.app.database import init_db
        init_db()
        print_success("Database initialized")
        return True
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False


def validate_config():
    """Validate configuration settings."""
    print_header("Validating Configuration")
    
    try:
        from backend.app.config import settings
        
        checks = {
            "Upload directory exists": settings.upload_dir.exists(),
            "Storage directory exists": settings.storage_dir.exists(),
            "Database URL configured": bool(settings.database_url),
            "Secret key set": len(settings.secret_key) > 10,
            "JWT algorithm configured": settings.algorithm == "HS256",
        }
        
        all_ok = True
        for check_name, result in checks.items():
            if result:
                print_success(check_name)
            else:
                print_warning(check_name)
                all_ok = False
        
        if not all_ok:
            print_warning("Some configuration items may need attention")
        
        return True
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")
        return False


def verify_modules():
    """Verify all enhanced modules are available."""
    print_header("Verifying Enhanced Modules")
    
    modules = [
        ("Cache", "backend.app.services.cache"),
        ("Advanced Analysis", "backend.app.services.advanced_analysis"),
        ("Export", "backend.app.services.export"),
        ("Batch Processing", "backend.app.services.batch"),
        ("Enhanced Runner", "backend.app.services.runner"),
        ("Export Routes", "backend.app.routes.export"),
    ]
    
    all_ok = True
    for module_name, module_path in modules:
        try:
            __import__(module_path)
            print_success(f"{module_name} module available")
        except ImportError as e:
            print_error(f"{module_name} module not found: {e}")
            all_ok = False
    
    return all_ok


def test_imports():
    """Test critical imports."""
    print_header("Testing Critical Imports")
    
    try:
        from fastapi import FastAPI
        print_success("FastAPI")
        
        from sqlalchemy.orm import Session
        print_success("SQLAlchemy")
        
        import pandas as pd
        print_success("Pandas")
        
        import numpy as np
        print_success("NumPy")
        
        from sklearn.decomposition import PCA
        print_success("scikit-learn")
        
        import scipy
        print_success("SciPy")
        
        return True
    except ImportError as e:
        print_error(f"Import failed: {e}")
        return False


def generate_setup_report():
    """Generate a setup report."""
    print_header("Setup Report")
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "directories": {
            "uploads": str(Path("backend/uploads").resolve()),
            "storage": str(Path("backend/storage").resolve()),
        },
    }
    
    report_file = Path("setup_report.json")
    with report_file.open("w") as f:
        json.dump(report, f, indent=2)
    
    print_success(f"Setup report saved to {report_file}")
    return True


def print_next_steps():
    """Print next steps for running the application."""
    print_header("Next Steps")
    
    print("""
1. Start the server:
   cd backend
   uvicorn app.main:app --reload --port 8000

2. Open in browser:
   http://localhost:8000

3. Create an account and start analyzing!

4. For more information, see:
   - ENHANCEMENTS.md (detailed features)
   - QUICK_START_ENHANCED.md (quick reference)
   - docs/ARCHITECTURE.md (system design)
    """)


def main():
    """Run complete setup."""
    print_header("SingleCellX Enhanced Edition - Setup")
    
    steps = [
        ("Python Version", check_python_version),
        ("Installing Dependencies", install_dependencies),
        ("Setting Up Directories", setup_directories),
        ("Testing Imports", test_imports),
        ("Verifying Modules", verify_modules),
        ("Initializing Database", init_database),
        ("Validating Configuration", validate_config),
        ("Generating Report", generate_setup_report),
    ]
    
    completed = []
    failed = []
    
    for step_name, step_func in steps:
        try:
            if step_func():
                completed.append(step_name)
            else:
                failed.append(step_name)
        except Exception as e:
            print_error(f"{step_name} raised exception: {e}")
            failed.append(step_name)
    
    # Summary
    print_header("Setup Summary")
    print(f"✅ Completed: {len(completed)}/{len(steps)}")
    
    if completed:
        for item in completed:
            print(f"  ✓ {item}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(steps)}")
        for item in failed:
            print(f"  ✗ {item}")
    
    if not failed:
        print_success("\n🎉 Setup completed successfully!")
        print_next_steps()
        return 0
    else:
        print_error("\n⚠️  Setup completed with errors")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
