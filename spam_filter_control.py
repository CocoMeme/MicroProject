#!/usr/bin/env python3
"""
Spam Filter Control Script
"""

import requests
import json
import sys

def get_spam_filter_config():
    """Get current spam filter configuration"""
    try:
        response = requests.get("http://localhost:5000/api/spam-filter")
        if response.status_code == 200:
            config = response.json()
            print("📋 Current Spam Filter Configuration:")
            print("=" * 40)
            print(f"Enabled: {config['spam_filter']['enabled']}")
            print(f"Min Weight Threshold: {config['spam_filter']['min_weight_threshold']}kg")
            print(f"Weight Change Threshold: {config['spam_filter']['weight_change_threshold']}kg")
            print()
            print("📝 Description:")
            for key, desc in config['description'].items():
                print(f"  {key}: {desc}")
            return config['spam_filter']
        else:
            print(f"❌ Failed to get config: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def update_spam_filter_config(enabled=None, min_weight=None, weight_change=None):
    """Update spam filter configuration"""
    try:
        data = {}
        if enabled is not None:
            data['enabled'] = enabled
        if min_weight is not None:
            data['min_weight_threshold'] = min_weight
        if weight_change is not None:
            data['weight_change_threshold'] = weight_change
        
        if not data:
            print("❌ No configuration changes provided")
            return False
        
        response = requests.post("http://localhost:5000/api/spam-filter", json=data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Spam filter configuration updated successfully!")
            print("📋 New Configuration:")
            config = result['new_config']
            print(f"  Enabled: {config['enabled']}")
            print(f"  Min Weight Threshold: {config['min_weight_threshold']}kg")
            print(f"  Weight Change Threshold: {config['weight_change_threshold']}kg")
            return True
        else:
            print(f"❌ Failed to update config: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🛡️ MQTT Spam Filter Control")
    print("=" * 40)
    
    if len(sys.argv) == 1:
        # No arguments - show current config
        get_spam_filter_config()
        print("\nUsage:")
        print("  python spam_filter_control.py [options]")
        print("\nOptions:")
        print("  --enable              Enable spam filtering")
        print("  --disable             Disable spam filtering")
        print("  --min-weight X        Set minimum weight threshold (kg)")
        print("  --weight-change X     Set weight change threshold (kg)")
        print("  --reset               Reset to default values")
        print("\nExamples:")
        print("  python spam_filter_control.py --enable")
        print("  python spam_filter_control.py --min-weight 0.2")
        print("  python spam_filter_control.py --disable --min-weight 0.05")
        return
    
    # Parse arguments
    enabled = None
    min_weight = None
    weight_change = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '--enable':
            enabled = True
        elif arg == '--disable':
            enabled = False
        elif arg == '--min-weight':
            if i + 1 < len(sys.argv):
                min_weight = float(sys.argv[i + 1])
                i += 1
            else:
                print("❌ --min-weight requires a value")
                return
        elif arg == '--weight-change':
            if i + 1 < len(sys.argv):
                weight_change = float(sys.argv[i + 1])
                i += 1
            else:
                print("❌ --weight-change requires a value")
                return
        elif arg == '--reset':
            enabled = True
            min_weight = 0.1
            weight_change = 0.05
            print("🔄 Resetting to default values...")
        else:
            print(f"❌ Unknown argument: {arg}")
            return
        
        i += 1
    
    # Update configuration
    if update_spam_filter_config(enabled, min_weight, weight_change):
        print("\n🎉 Configuration updated successfully!")
        print("The spam filter settings are now active.")
    else:
        print("\n❌ Failed to update configuration.")

if __name__ == "__main__":
    main()
