#!/usr/bin/env python3
"""
Request History Manager
A tool to save, search, and reuse your AI assistant requests.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import argparse


class RequestHistory:
    def __init__(self, history_file: str = None):
        """Initialize the request history manager."""
        if history_file is None:
            home = Path.home()
            self.history_dir = home / ".cursor_history"
            self.history_dir.mkdir(exist_ok=True)
            self.history_file = self.history_dir / "requests.json"
        else:
            self.history_file = Path(history_file)
            self.history_dir = self.history_file.parent
            self.history_dir.mkdir(parents=True, exist_ok=True)
        
        self.requests = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load request history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.history_file}, starting fresh.", file=sys.stderr)
                return []
        return []
    
    def _save_history(self):
        """Save request history to file."""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.requests, f, indent=2, ensure_ascii=False)
    
    def add_request(self, request: str, tags: List[str] = None, description: str = None) -> int:
        """Add a new request to history."""
        request_id = len(self.requests) + 1
        entry = {
            "id": request_id,
            "timestamp": datetime.now().isoformat(),
            "request": request,
            "tags": tags or [],
            "description": description or ""
        }
        self.requests.append(entry)
        self._save_history()
        return request_id
    
    def get_request(self, request_id: int) -> Optional[Dict]:
        """Get a specific request by ID."""
        for req in self.requests:
            if req["id"] == request_id:
                return req
        return None
    
    def search_requests(self, query: str = None, tag: str = None) -> List[Dict]:
        """Search requests by text or tag."""
        results = self.requests.copy()
        
        if query:
            query_lower = query.lower()
            results = [
                r for r in results 
                if query_lower in r["request"].lower() 
                or query_lower in r.get("description", "").lower()
            ]
        
        if tag:
            tag_lower = tag.lower()
            results = [
                r for r in results 
                if any(tag_lower == t.lower() for t in r.get("tags", []))
            ]
        
        return results
    
    def list_recent(self, count: int = 10) -> List[Dict]:
        """Get the most recent requests."""
        return self.requests[-count:] if len(self.requests) > count else self.requests
    
    def delete_request(self, request_id: int) -> bool:
        """Delete a request by ID."""
        for i, req in enumerate(self.requests):
            if req["id"] == request_id:
                self.requests.pop(i)
                self._save_history()
                return True
        return False
    
    def update_request(self, request_id: int, request: str = None, 
                      tags: List[str] = None, description: str = None) -> bool:
        """Update an existing request."""
        for req in self.requests:
            if req["id"] == request_id:
                if request is not None:
                    req["request"] = request
                if tags is not None:
                    req["tags"] = tags
                if description is not None:
                    req["description"] = description
                req["updated"] = datetime.now().isoformat()
                self._save_history()
                return True
        return False
    
    def export_history(self, output_file: str):
        """Export history to a file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.requests, f, indent=2, ensure_ascii=False)
        print(f"History exported to {output_file}")
    
    def import_history(self, input_file: str, merge: bool = False):
        """Import history from a file."""
        with open(input_file, 'r', encoding='utf-8') as f:
            imported = json.load(f)
        
        if merge:
            # Merge with existing, reassigning IDs
            max_id = max([r["id"] for r in self.requests], default=0)
            for entry in imported:
                max_id += 1
                entry["id"] = max_id
                self.requests.append(entry)
        else:
            self.requests = imported
        
        self._save_history()
        print(f"Imported {len(imported)} requests")


def format_request(req: Dict, verbose: bool = False) -> str:
    """Format a request for display."""
    timestamp = datetime.fromisoformat(req["timestamp"]).strftime("%Y-%m-%d %H:%M")
    tags_str = f" [{', '.join(req['tags'])}]" if req.get('tags') else ""
    
    lines = [f"[{req['id']}] {timestamp}{tags_str}"]
    
    if verbose:
        if req.get('description'):
            lines.append(f"  Description: {req['description']}")
        lines.append(f"  Request: {req['request']}")
    else:
        # Show first 100 chars of request
        request_preview = req['request'][:100]
        if len(req['request']) > 100:
            request_preview += "..."
        lines.append(f"  {request_preview}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Manage your AI assistant request history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Save a new request
  %(prog)s add "Create a REST API with FastAPI" --tags api python

  # List recent requests
  %(prog)s list --count 20

  # Search for requests
  %(prog)s search "API"

  # Get a specific request
  %(prog)s get 5

  # Copy a request to clipboard (requires xclip or pbcopy)
  %(prog)s get 5 --copy
        """
    )
    
    parser.add_argument('--file', help='Custom history file location')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new request')
    add_parser.add_argument('request', help='The request text')
    add_parser.add_argument('--tags', nargs='+', help='Tags for the request')
    add_parser.add_argument('--description', help='Description of the request')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent requests')
    list_parser.add_argument('--count', type=int, default=10, help='Number of requests to show')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Show full requests')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search requests')
    search_parser.add_argument('query', nargs='?', help='Search query')
    search_parser.add_argument('--tag', help='Filter by tag')
    search_parser.add_argument('--verbose', '-v', action='store_true', help='Show full requests')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get a specific request')
    get_parser.add_argument('id', type=int, help='Request ID')
    get_parser.add_argument('--copy', action='store_true', help='Copy to clipboard')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a request')
    delete_parser.add_argument('id', type=int, help='Request ID')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update a request')
    update_parser.add_argument('id', type=int, help='Request ID')
    update_parser.add_argument('--request', help='New request text')
    update_parser.add_argument('--tags', nargs='+', help='New tags')
    update_parser.add_argument('--description', help='New description')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export history')
    export_parser.add_argument('output', help='Output file')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import history')
    import_parser.add_argument('input', help='Input file')
    import_parser.add_argument('--merge', action='store_true', help='Merge with existing history')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    history = RequestHistory(args.file)
    
    if args.command == 'add':
        request_id = history.add_request(args.request, args.tags, args.description)
        print(f"Request saved with ID: {request_id}")
    
    elif args.command == 'list':
        requests = history.list_recent(args.count)
        if not requests:
            print("No requests found.")
        else:
            for req in reversed(requests):  # Most recent first
                print(format_request(req, args.verbose))
                print()
    
    elif args.command == 'search':
        requests = history.search_requests(args.query, args.tag)
        if not requests:
            print("No matching requests found.")
        else:
            print(f"Found {len(requests)} matching request(s):\n")
            for req in reversed(requests):  # Most recent first
                print(format_request(req, args.verbose))
                print()
    
    elif args.command == 'get':
        req = history.get_request(args.id)
        if not req:
            print(f"Request {args.id} not found.")
            sys.exit(1)
        
        print(format_request(req, verbose=True))
        
        if args.copy:
            try:
                import subprocess
                # Try different clipboard commands
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['pbcopy'], input=req['request'].encode(), check=True)
                elif sys.platform.startswith('linux'):  # Linux
                    subprocess.run(['xclip', '-selection', 'clipboard'], 
                                 input=req['request'].encode(), check=True)
                else:  # Windows
                    subprocess.run(['clip'], input=req['request'].encode(), check=True)
                print("\n✓ Copied to clipboard!")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("\n✗ Could not copy to clipboard. Install xclip (Linux) or pbcopy (macOS)")
    
    elif args.command == 'delete':
        if history.delete_request(args.id):
            print(f"Request {args.id} deleted.")
        else:
            print(f"Request {args.id} not found.")
    
    elif args.command == 'update':
        if history.update_request(args.id, args.request, args.tags, args.description):
            print(f"Request {args.id} updated.")
        else:
            print(f"Request {args.id} not found.")
    
    elif args.command == 'export':
        history.export_history(args.output)
    
    elif args.command == 'import':
        history.import_history(args.input, args.merge)


if __name__ == '__main__':
    main()
