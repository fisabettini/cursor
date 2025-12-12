# Examples: Request History Manager

Here are some practical examples to get you started with the Request History Manager.

## Scenario 1: Daily Development Work

### Monday - Starting a new feature
```bash
./request_history.py add "Create a user authentication system with JWT tokens, refresh tokens, and password reset functionality" --tags auth backend security --description "New feature for v2.0 release"
# Output: Request saved with ID: 1
```

### Tuesday - Need to modify the request
```bash
./request_history.py list
# See your requests

./request_history.py get 1 --copy
# Copy it, paste in chat, and modify: "Also add OAuth2 support for Google and GitHub"
```

### Wednesday - Add related request
```bash
./request_history.py add "Add rate limiting to authentication endpoints to prevent brute force attacks" --tags auth security backend --description "Security enhancement for auth system"
```

### Friday - Search for all auth-related work
```bash
./request_history.py search --tag auth
# Shows all your authentication-related requests
```

## Scenario 2: Bug Fixes

### Reporting a bug
```bash
./request_history.py add "Fix: Users with email addresses containing '+' symbol cannot register" --tags bugfix auth --description "Priority: High - Blocking production deployment"
```

### Finding bug-related requests later
```bash
./request_history.py search "fix" --verbose
# or
./request_history.py search --tag bugfix
```

## Scenario 3: Frontend Development

```bash
# Day 1
./request_history.py add "Create a responsive dashboard with sidebar navigation, dark mode toggle, and user profile section" --tags frontend react ui

# Day 2
./request_history.py add "Add charts to dashboard using Chart.js - revenue over time and user growth metrics" --tags frontend react charts

# Day 3
./request_history.py add "Implement infinite scroll for the activity feed on dashboard" --tags frontend react optimization

# Later - find all frontend work
./request_history.py search --tag frontend --verbose
```

## Scenario 4: API Development

```bash
# Create initial API
./request_history.py add "Build REST API with these endpoints: GET/POST /users, GET/POST/PUT/DELETE /products, GET /orders" --tags api backend rest

# Later - extend it
./request_history.py get 1
./request_history.py update 1 --request "Build REST API with these endpoints: GET/POST /users, GET/POST/PUT/DELETE /products, GET/POST /orders, GET /analytics"

# Add documentation request
./request_history.py add "Generate OpenAPI/Swagger documentation for the REST API" --tags api documentation backend
```

## Scenario 5: Database Work

```bash
# Schema design
./request_history.py add "Design PostgreSQL database schema for e-commerce app with tables: users, products, orders, order_items, reviews, and categories. Include proper foreign keys and indexes." --tags database postgresql schema

# Migration
./request_history.py add "Create Alembic migration to add 'featured' boolean column to products table and 'wishlist' table" --tags database migration postgresql

# Query optimization
./request_history.py add "Optimize the slow product search query - add full-text search and proper indexes" --tags database optimization postgresql
```

## Scenario 6: DevOps Tasks

```bash
./request_history.py add "Create Dockerfile for Node.js app with multi-stage build, non-root user, and minimal image size" --tags devops docker nodejs

./request_history.py add "Set up GitHub Actions CI/CD pipeline: run tests, build Docker image, deploy to staging" --tags devops ci-cd github-actions

./request_history.py add "Create Kubernetes manifests for deployment with 3 replicas, health checks, and resource limits" --tags devops kubernetes deployment
```

## Scenario 7: Data Analysis

```bash
./request_history.py add "Analyze sales CSV data: calculate monthly revenue, identify top 10 products, create bar chart visualization" --tags python data-analysis pandas

./request_history.py add "Create Python script to clean customer data: remove duplicates, validate emails, standardize phone numbers" --tags python data-cleaning pandas

./request_history.py add "Generate weekly report from database: active users, conversion rate, average order value - export to PDF" --tags python reporting data-analysis
```

## Scenario 8: Team Collaboration

```bash
# Team lead saves templates
./request_history.py add "Code review checklist: Check error handling, add unit tests, verify security best practices, ensure documentation is updated" --tags template code-review

./request_history.py add "Create pull request template with sections: Description, Changes, Testing, Screenshots" --tags template pr documentation

# Export to share with team
./request_history.py export team-templates.json

# Team member imports
./request_history.py import team-templates.json --merge
```

## Scenario 9: Learning & Tutorials

```bash
./request_history.py add "Explain how async/await works in JavaScript with examples" --tags learning javascript async

./request_history.py add "Show me best practices for React hooks - useState, useEffect, useCallback, useMemo" --tags learning react hooks

./request_history.py add "Create tutorial: Deploy Flask app to AWS with RDS database and load balancer" --tags tutorial aws flask deployment

# Later search for learning resources
./request_history.py search --tag learning
```

## Scenario 10: Regular Maintenance Tasks

```bash
# Create templates for recurring tasks
./request_history.py add "Update all npm dependencies to latest versions, check for breaking changes, run test suite" --tags maintenance nodejs template

./request_history.py add "Monthly security audit: check dependencies for vulnerabilities, review user permissions, verify SSL certificates" --tags maintenance security template

./request_history.py add "Database backup and cleanup: backup production DB, delete old logs (>90 days), vacuum tables" --tags maintenance database template

# Quick access to templates
./request_history.py search --tag template
```

## Pro Tips from Examples

### Use Consistent Tags
- `frontend`, `backend`, `database`, `devops`
- `bugfix`, `feature`, `optimization`
- `urgent`, `template`, `learning`

### Add Context in Descriptions
```bash
./request_history.py add "..." --description "Related to ticket #1234" 
./request_history.py add "..." --description "Client: Acme Corp"
./request_history.py add "..." --description "Deadline: End of sprint"
```

### Create Templates
Save commonly used request patterns with the `template` tag:
```bash
./request_history.py add "Create REST API endpoint: [METHOD] [PATH] with [PARAMS]" --tags template api
./request_history.py add "Fix bug: [DESCRIPTION] in [COMPONENT]" --tags template bugfix
```

### Export Before Major Changes
```bash
# Weekly backup
./request_history.py export ~/backups/requests-$(date +%Y%m%d).json
```

### Workflow Integration
```bash
# Search → Copy → Use → Update cycle
./request_history.py search "API"           # Find related request
./request_history.py get 5 --copy          # Copy it
# [Use in chat with modifications]
./request_history.py add "Enhanced version: ..."  # Save the improved version
```
