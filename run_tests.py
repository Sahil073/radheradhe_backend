"""
Test runner script
"""

import pytest
import sys
import os

# Add the backend-flask directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Run tests with verbose output
    exit_code = pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    sys.exit(exit_code)