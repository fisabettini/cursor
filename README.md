# Request History Manager

Never lose your AI assistant requests again! This tool saves all your requests so you can easily reuse and modify them later.

## Quick Start

### Installation

1. **Make the script executable:**
   ```bash
   chmod +x request_history.py
   ```

2. **Optional: Add to your PATH for easy access**
   ```bash
   # Add an alias to your ~/.bashrc or ~/.zshrc
   echo 'alias rh="/workspace/request_history.py"' >> ~/.bashrc
   source ~/.bashrc
   ```

   Or create a symlink:
   ```bash
   sudo ln -s /workspace/request_history.py /usr/local/bin/rh
   ```

### Basic Usage

#### Save a Request
```bash
./request_history.py add "Create a REST API with FastAPI for user management"
```

With tags:
```bash
./request_history.py add "Build a React dashboard with charts" --tags react frontend dashboard
```

With description:
```bash
./request_history.py add "Fix the login bug" --description "Users can't login with special characters in password"
```

#### List Your Recent Requests
```bash
./request_history.py list
```

Show more:
```bash
./request_history.py list --count 20
```

Show full requests (not just preview):
```bash
./request_history.py list --verbose
```

#### Search Requests
```bash
./request_history.py search "API"
```

Search by tag:
```bash
./request_history.py search --tag react
```

Combined search:
```bash
./request_history.py search "dashboard" --tag frontend
```

#### Get a Specific Request
```bash
./request_history.py get 5
```

Copy to clipboard:
```bash
./request_history.py get 5 --copy
```

#### Update a Request
```bash
./request_history.py update 5 --request "Create a REST API with FastAPI and PostgreSQL"
./request_history.py update 5 --tags api python postgresql
./request_history.py update 5 --description "Updated to include database"
```

#### Delete a Request
```bash
./request_history.py delete 5
```

#### Export/Import
```bash
# Export to backup
./request_history.py export backup.json

# Import (replace current history)
./request_history.py import backup.json

# Import and merge with existing
./request_history.py import backup.json --merge
```

## Features

✨ **Automatic Timestamping** - Every request is timestamped so you know when you made it

🏷️ **Tags** - Organize requests with tags like `api`, `frontend`, `bugfix`, etc.

🔍 **Search** - Find requests by text or tags

📋 **Copy to Clipboard** - Quickly copy a request to reuse it

💾 **Export/Import** - Back up your history or share it across machines

📝 **Descriptions** - Add notes to remember context

## Workflow Example

```bash
# Day 1: Save your request
./request_history.py add "Create a Python script to analyze CSV files and generate reports" --tags python data-analysis

# Day 3: Find it again
./request_history.py search "CSV"
# Output: [1] 2025-12-10 14:30 [python, data-analysis]
#   Create a Python script to analyze CSV files and generate reports

# Retrieve it
./request_history.py get 1 --copy
# Now paste it and modify as needed!

# Day 5: Update with new requirements
./request_history.py update 1 --request "Create a Python script to analyze CSV files, generate reports, and send email notifications" --tags python data-analysis email
```

## Storage Location

Requests are stored in: `~/.cursor_history/requests.json`

You can use a custom location:
```bash
./request_history.py --file ~/my-custom-location/requests.json add "My request"
```

## Tips

1. **Use descriptive tags** - They make searching much easier
   - Good: `api`, `frontend`, `database`, `bugfix`, `feature`
   - Not helpful: `work`, `stuff`, `code`

2. **Add descriptions for complex requests** - Your future self will thank you

3. **Regular backups** - Export your history occasionally:
   ```bash
   ./request_history.py export ~/backups/requests-$(date +%Y%m%d).json
   ```

4. **Set up an alias** - `rh` is much faster to type than `./request_history.py`

## Requirements

- Python 3.6 or higher (already included in most systems)
- For clipboard support: `xclip` on Linux or `pbcopy` on macOS (usually pre-installed)

## Troubleshooting

**"Permission denied" error:**
```bash
chmod +x request_history.py
```

**Clipboard not working on Linux:**
```bash
sudo apt-get install xclip  # Ubuntu/Debian
sudo yum install xclip      # CentOS/RHEL
```

**Can't find the command:**
Make sure you're in the right directory or add it to your PATH (see Installation above)

## Advanced Usage

### Combine with Your Workflow

Create a shell function in your `~/.bashrc`:
```bash
ask() {
    rh add "$1" --tags "${@:2}"
    echo "Request saved! Now copy-paste it to your AI assistant."
}
```

Then use it like:
```bash
ask "Create a login system with 2FA" auth security
```

### Integration with Other Tools

Export to share with your team:
```bash
./request_history.py export team-requests.json
```

Filter and process with `jq`:
```bash
cat ~/.cursor_history/requests.json | jq '.[] | select(.tags[] == "urgent")'
```

## License

Free to use and modify as needed!
