# PostgreSQL Setup for Crawler Service

## Overview

The crawler service uses PostgreSQL with the pgvector extension for storing crawled content and vector embeddings. This enables semantic search capabilities for crawled content.

## Database Configuration

### Environment Variables

Configure the following in your `.env` file:

```env
DATABASE_URL=postgresql://crawler_user:crawler_password@postgres:5432/crawler_db
VECTOR_STORAGE_ENABLED=true
REDIS_URL=redis://redis:6379
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

### Docker Compose Services

The `docker-compose.yml` includes:

1. **PostgreSQL** - Main database with pgvector extension
   - Port: 5435 (external) -> 5432 (internal)
   - User: `crawler_user`
   - Password: `crawler_password`
   - Database: `crawler_db`

2. **Redis** - Caching layer
   - Port: 6381 (external) -> 6379 (internal)

3. **Crawler Service** - Main application
   - Port: 8001

## Database Schema

### Table: `crawled_content`

Stores crawled web pages with their embeddings:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| url | VARCHAR(2048) | Page URL (unique, indexed) |
| title | VARCHAR(512) | Page title |
| text_content | TEXT | Full text content |
| content_snippet | TEXT | Content preview |
| base_url | VARCHAR(512) | Base domain URL (indexed) |
| images_count | INTEGER | Number of images found |
| crawl_timestamp | TIMESTAMP | When page was crawled |
| embedding | VECTOR(384) | Text embedding for similarity search |

### Indexes

- `url` - B-tree index for fast URL lookups
- `base_url` - B-tree index for domain filtering
- `embedding` - IVFFlat index for vector similarity search (cosine distance)

## Setup Instructions

### Option 1: Using Docker Compose (Recommended)

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Check logs:**
   ```bash
   docker-compose logs -f crawler
   ```

3. **Access the service:**
   - API: http://localhost:8001
   - Docs: http://localhost:8001/docs
   - Health: http://localhost:8001/health

### Option 2: Manual Setup

1. **Start only the database:**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Update `.env` for local development:**
   ```env
   DATABASE_URL=postgresql://crawler_user:crawler_password@localhost:5435/crawler_db
   REDIS_URL=redis://localhost:6381
   ```

3. **Run the service locally:**
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8001
   ```

## Database Management

### Connect to PostgreSQL

Using psql:
```bash
docker exec -it crawler-postgres psql -U crawler_user -d crawler_db
```

### Common Commands

Check pgvector extension:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

View tables:
```sql
\dt
```

Check table structure:
```sql
\d crawled_content
```

Query crawled pages:
```sql
SELECT id, url, title, crawl_timestamp FROM crawled_content LIMIT 10;
```

Count crawled pages:
```sql
SELECT COUNT(*) FROM crawled_content;
```

### Backup and Restore

**Backup:**
```bash
docker exec crawler-postgres pg_dump -U crawler_user crawler_db > backup.sql
```

**Restore:**
```bash
cat backup.sql | docker exec -i crawler-postgres psql -U crawler_user -d crawler_db
```

## Vector Search

The service supports semantic search using embeddings:

### Example Search Query

```python
from sqlalchemy import select, func
from pgvector.sqlalchemy import Vector

# Generate query embedding
query_embedding = model.encode("search query")

# Find similar documents
stmt = (
    select(CrawledContent)
    .order_by(CrawledContent.embedding.cosine_distance(query_embedding))
    .limit(10)
)
results = session.execute(stmt).scalars().all()
```

## Troubleshooting

### Database Connection Issues

1. **Check container status:**
   ```bash
   docker-compose ps
   ```

2. **View database logs:**
   ```bash
   docker-compose logs postgres
   ```

3. **Test connection:**
   ```bash
   docker exec crawler-postgres pg_isready -U crawler_user
   ```

### pgvector Extension Issues

1. **Verify installation:**
   ```bash
   docker exec crawler-postgres psql -U crawler_user -d crawler_db -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
   ```

2. **Manual installation (if needed):**
   ```bash
   docker exec -it crawler-postgres bash
   # Inside container, the setup_pgvector.sh script should have run automatically
   ```

### Reset Database

**Warning:** This will delete all data!

```bash
docker-compose down -v
docker-compose up -d
```

## Performance Optimization

### Connection Pooling

The service uses SQLAlchemy connection pooling:
- Pool size: 5 connections
- Max overflow: 10 connections
- Pre-ping enabled for connection health checks

### Vector Index Tuning

For better performance with large datasets:

```sql
-- Adjust IVFFlat lists parameter based on dataset size
-- Rule of thumb: lists ≈ sqrt(total_rows)
CREATE INDEX idx_embedding_vector ON crawled_content 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 1000);
```

## Related Files

- [docker-compose.yml](docker-compose.yml) - Service orchestration
- [setup_pgvector.sh](setup_pgvector.sh) - pgvector installation script
- [app/core/database.py](app/core/database.py) - Database connection setup
- [app/core/config.py](app/core/config.py) - Configuration settings
- [app/models/crawled_content.py](app/models/crawled_content.py) - Database models
- [app/services/vector_db_service.py](app/services/vector_db_service.py) - Database operations

## Architecture Reference

This setup follows the same patterns as:
- `authentications/` service - Database and Redis configuration
- `app-service/` - Connection pooling and session management
