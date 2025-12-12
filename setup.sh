#!/bin/bash
# Quick setup script for Request History Manager

echo "🚀 Setting up Request History Manager..."
echo

# Make the script executable
chmod +x request_history.py
echo "✓ Made request_history.py executable"

# Detect shell
SHELL_RC=""
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
else
    echo "⚠️  Could not detect shell type. Please add alias manually."
fi

# Add alias if shell detected
if [ -n "$SHELL_RC" ]; then
    ALIAS_LINE="alias rh='$(pwd)/request_history.py'"
    
    if grep -q "alias rh=" "$SHELL_RC" 2>/dev/null; then
        echo "⚠️  Alias 'rh' already exists in $SHELL_RC"
    else
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        echo "✓ Added alias 'rh' to $SHELL_RC"
        echo
        echo "📝 To use the alias in this session, run:"
        echo "   source $SHELL_RC"
    fi
fi

echo
echo "✅ Setup complete!"
echo
echo "Try it out:"
echo "  ./request_history.py add \"Your first request\" --tags example"
echo "  ./request_history.py list"
echo
echo "Or use the alias (after sourcing your shell config):"
echo "  rh add \"Your first request\""
echo
echo "📖 Read README.md for more information"
