# Accessing PostgreSQL 17 Docker Container with pgAdmin4

This guide explains how to connect to a PostgreSQL 17 instance running in a Docker container using pgAdmin4, treating the container as a remote server.

## Prerequisites

- PostgreSQL 17 running in a Docker container
- pgAdmin4 installed on your host machine (or running in another container)

## Method 1: Using Host Port Mapping (Recommended)

### Step 1: Ensure PostgreSQL Container Exposes the Port

When running your PostgreSQL container, make sure to map the PostgreSQL port (5432) to your host:

```bash
docker run -d \
  --name postgres17 \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  postgres:17
```

If your container is already running without port mapping, you'll need to recreate it with the `-p 5432:5432` flag, or use Method 2.

### Step 2: Configure pgAdmin4 Connection

1. Open pgAdmin4
2. Right-click on "Servers" → "Register" → "Server..."
3. In the **General** tab:
   - Name: `PostgreSQL Docker` (or any name you prefer)
4. In the **Connection** tab:
   - Host name/address: `localhost` (or `127.0.0.1`)
   - Port: `5432`
   - Maintenance database: `postgres` (or your database name)
   - Username: Your PostgreSQL username
   - Password: Your PostgreSQL password
5. Click "Save"

## Method 2: Using Docker Container IP Address

If you can't use port mapping, you can connect directly to the container's IP.

### Step 1: Find the Container's IP Address

```bash
# Get container IP address
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_name_or_id>

# Or get more detailed network info
docker inspect <container_name_or_id> | grep IPAddress
```

### Step 2: Configure PostgreSQL to Accept Remote Connections

You may need to modify PostgreSQL's configuration to accept connections from outside the container.

#### Option A: Using Docker Environment Variables

When starting the container, you can set:

```bash
docker run -d \
  --name postgres17 \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  postgres:17 \
  -c listen_addresses='*'
```

#### Option B: Modifying Configuration Files

If the container is already running:

```bash
# Access the container shell
docker exec -it <container_name> bash

# Edit postgresql.conf (inside container)
echo "listen_addresses = '*'" >> /var/lib/postgresql/data/postgresql.conf

# Edit pg_hba.conf to allow connections (inside container)
echo "host all all 0.0.0.0/0 md5" >> /var/lib/postgresql/data/pg_hba.conf

# Exit container
exit

# Restart the container
docker restart <container_name>
```

### Step 3: Configure pgAdmin4

Use the container's IP address (from Step 1) as the host in pgAdmin4's connection settings.

## Method 3: Using Docker Network (Best for pgAdmin4 in Docker)

If pgAdmin4 is also running in Docker, use a shared network.

### Step 1: Create a Docker Network

```bash
docker network create pg-network
```

### Step 2: Run PostgreSQL on the Network

```bash
docker run -d \
  --name postgres17 \
  --network pg-network \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  postgres:17
```

### Step 3: Run pgAdmin4 on the Same Network

```bash
docker run -d \
  --name pgadmin \
  --network pg-network \
  -e PGADMIN_DEFAULT_EMAIL=admin@admin.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin \
  -p 8080:80 \
  dpage/pgadmin4
```

### Step 4: Connect in pgAdmin4

1. Open pgAdmin4 at `http://localhost:8080`
2. Login with your pgAdmin credentials
3. Register a new server with:
   - Host: `postgres17` (the container name)
   - Port: `5432`
   - Username/Password: Your PostgreSQL credentials

## Using Docker Compose (Recommended for Development)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:17
    container_name: postgres17
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - pg-network

  pgadmin:
    image: dpage/pgadmin4
    container_name: pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@admin.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "8080:80"
    depends_on:
      - postgres
    networks:
      - pg-network

networks:
  pg-network:
    driver: bridge

volumes:
  postgres_data:
```

Start with:

```bash
docker-compose up -d
```

Then access pgAdmin4 at `http://localhost:8080` and connect to host `postgres` on port `5432`.

## Troubleshooting

### Connection Refused

1. Verify the container is running:
   ```bash
   docker ps
   ```

2. Check PostgreSQL logs:
   ```bash
   docker logs <container_name>
   ```

3. Verify port mapping:
   ```bash
   docker port <container_name>
   ```

### Authentication Failed

1. Verify your username and password
2. Check `pg_hba.conf` allows your connection method
3. Try connecting via `psql` first to verify credentials:
   ```bash
   docker exec -it <container_name> psql -U myuser -d mydb
   ```

### Cannot Connect to Container IP from Host

On some systems (especially Docker Desktop on macOS/Windows), you cannot directly access container IPs from the host. Use port mapping (Method 1) instead.

## Quick Reference: pgAdmin4 Connection Settings

| Setting | Value (Port Mapping) | Value (Docker Network) |
|---------|---------------------|------------------------|
| Host | `localhost` or `127.0.0.1` | Container name (e.g., `postgres17`) |
| Port | `5432` | `5432` |
| Database | `postgres` or your DB name | `postgres` or your DB name |
| Username | Your POSTGRES_USER | Your POSTGRES_USER |
| Password | Your POSTGRES_PASSWORD | Your POSTGRES_PASSWORD |
