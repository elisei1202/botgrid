#!/usr/bin/env python3
"""
Quick fix for config.yaml structure
Moves 'profiles' under 'grid' section
"""

import yaml
import os

config_file = "config.yaml"

if not os.path.exists(config_file):
    print(f"❌ File not found: {config_file}")
    exit(1)

print("🔧 Fixing config.yaml structure...")

# Read current config
with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

# Check if profiles is at root level
if 'profiles' in config and 'profiles' not in config.get('grid', {}):
    print("📝 Moving 'profiles' under 'grid' section...")
    
    # Move profiles under grid
    if 'grid' not in config:
        config['grid'] = {}
    
    config['grid']['profiles'] = config.pop('profiles')
    
    # Write back
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("✅ Config fixed successfully!")
    print("Structure: grid -> profiles -> (Conservative, Normal, Aggressive)")
else:
    print("ℹ️  Config structure already correct")

print("\n🚀 You can now run: python3 main.py")
