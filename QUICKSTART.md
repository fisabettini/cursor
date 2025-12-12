# Quick Reference - Request History Manager

## Installation (One Time)
```bash
chmod +x request_history.py
# Optional: Add alias to ~/.bashrc or ~/.zshrc
echo 'alias rh="/workspace/request_history.py"' >> ~/.bashrc
source ~/.bashrc
```

## Most Common Commands

### Save a request
```bash
./request_history.py add "Your request here"
./request_history.py add "Your request" --tags tag1 tag2 tag3
```

### List recent requests
```bash
./request_history.py list
./request_history.py list --count 20
```

### Search
```bash
./request_history.py search "keyword"
./request_history.py search --tag tagname
```

### Get specific request
```bash
./request_history.py get 5
./request_history.py get 5 --copy    # Copy to clipboard
```

### Update
```bash
./request_history.py update 5 --request "New text"
./request_history.py update 5 --tags new tags here
```

### Delete
```bash
./request_history.py delete 5
```

## Storage
Stored in: `~/.cursor_history/requests.json`

## With Alias (rh)
```bash
rh add "Your request"
rh list
rh search "keyword"
rh get 5 --copy
```

## Full Documentation
- `README.md` - Complete guide
- `EXAMPLES.md` - Real-world scenarios
- `./request_history.py --help` - Built-in help
