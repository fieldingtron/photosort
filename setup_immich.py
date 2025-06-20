#!/usr/bin/env python3
"""
Immich Upload Setup Script (Python version)
Checks for Node.js, npm, and installs Immich CLI.

Usage:
    python setup_immich.py
"""
import subprocess
import sys

def check_command(cmd):
    try:
        subprocess.run([cmd, '--version'], check=True, capture_output=True)
        return True
    except Exception:
        return False

def main():
    print("🚀 Immich Upload Setup\n=====================")
    if not check_command('node'):
        print("❌ Node.js not found. Please install Node.js first:")
        print("   Visit: https://nodejs.org/")
        print("   Or use Homebrew: brew install node")
        sys.exit(1)
    print("✅ Node.js found.")
    if not check_command('npm'):
        print("❌ npm not found. Please install npm.")
        sys.exit(1)
    print("✅ npm found.")
    print("📦 Installing Immich CLI...")
    result = subprocess.run(['npm', 'install', '-g', '@immich/cli'])
    if result.returncode == 0:
        print("✅ Immich CLI installed successfully!")
        print("\n📋 Next steps:")
        print("1. Make sure your Immich server is running")
        print("2. Get your API key from Immich web interface (User Settings → API Keys)")
        print("3. Run: python upload_to_immich.py --setup")
        print("4. Or run directly: python upload_to_immich.py . --server-url YOUR_URL --api-key YOUR_KEY")
    else:
        print("❌ Failed to install Immich CLI")
        sys.exit(1)

if __name__ == "__main__":
    main()
