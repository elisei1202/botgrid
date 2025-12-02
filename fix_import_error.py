#!/usr/bin/env python3
"""
Quick fix for missing 'Any' import in grid_logic.py
Run this script to automatically fix the import error
"""

import os

# Path to grid_logic.py
file_path = "modules/grid_logic.py"

if not os.path.exists(file_path):
    print(f"❌ File not found: {file_path}")
    print("Make sure you're running this from the bybit_grid_bot directory")
    exit(1)

# Read the file
with open(file_path, 'r') as f:
    content = f.read()

# Replace the import line
old_import = "from typing import Dict, List, Tuple, Optional"
new_import = "from typing import Dict, List, Tuple, Optional, Any"

if old_import in content and "Any" not in content.split('\n')[7]:
    content = content.replace(old_import, new_import)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Import fixed successfully!")
    print(f"Updated: {file_path}")
    print("Changed: from typing import Dict, List, Tuple, Optional, Any")
else:
    print("ℹ️  Import already correct or file structure different")
    print("No changes needed")
