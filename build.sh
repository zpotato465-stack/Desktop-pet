#!/usr/bin/env bash
# Build script for Duck Desktop Pet
# Run on the target platform (Windows or macOS)

set -euo pipefail

echo "🦆  Duck Desktop Pet — Build Script"
echo "======================================"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Platform detection
OS="$(uname -s)"
case "$OS" in
    Darwin*)
        echo "Building macOS .app..."
        pyinstaller --clean build_mac.spec
        echo ""
        echo "✅ Done! Find your app in:"
        echo "   dist/duck that carries you over a disproportionately small gap.app"
        echo ""
        echo "To create a DMG installer:"
        echo "   hdiutil create -volname 'Duck Pet' -srcfolder 'dist/duck that carries you over a disproportionately small gap.app' -ov -format UDZO 'dist/duck-pet.dmg'"
        ;;
    Linux*)
        echo "Building Linux binary (use Windows VM or cross-compile for .exe)..."
        pyinstaller --clean build_windows.spec
        echo "✅ Done! Binary at: dist/"
        ;;
    *)
        echo "Run this on macOS for .app, or on Windows for .exe"
        echo "Windows: pyinstaller --clean build_windows.spec"
        ;;
esac
