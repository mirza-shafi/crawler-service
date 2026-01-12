# Crawler Microservice Information

## Service Overview

**Service Name:** Crawler Microservice  
**Version:** 1.0.0  
**Port:** 8001  
**Framework:** FastAPI + Uvicorn  
**Python Version:** 3.11+

## Purpose

High-performance web crawler and scraper microservice that provides a structured API for:
- Recursive crawling of websites following internal links
- Automatic domain boundary enforcement
- Content extraction (titles, text, images)
- Concurrent page fetching with async operations
- Comprehensive error handling and metadata collection

Similar to Apify, but implemented as a lightweight microservice.

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.104.1 | Web framework |
| Uvicorn | 0.24.0 | ASGI server |
| httpx | 0.25.2 | Async HTTP client |
| beautifulsoup4 | 4.12.2 | HTML parsing |
| pydantic | 2.5.2 | Data validation |

## Architecture

### Layered Architecture Pattern

```
HTTP Layer (API)
    ↓
Business Logic (Services)
    ↓
Core Components (Config, Utils)
    ↓
Data Models & Schemas
```

### Directory Structure

```
app/
├── api/v1/endpoints/crawler.py      # REST endpoints
├── services/crawler.py               # Crawling logic
├── core/config.py                   # Configuration
├── schemas/crawler.py               # Request/Response models
├── models/                          # Data models
└── main.py                          # FastAPI app
```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Service information |
| GET | `/health` | Health check |
| GET | `/status` | Service status |
| GET | `/api/v1/crawler/health` | Crawler health |
| POST | `/api/v1/crawler/crawl` | Single crawl |
| POST | `/api/v1/crawler/crawl/batch` | Batch crawl |
| GET | `/api/v1/crawler/crawl/domains/{domain}` | Domain info |

### Documentation

| Endpoint | Purpose |
|----------|---------|
| `/docs` | Swagger UI (Interactive API docs) |
| `/redoc` | ReDoc (Alternative API docs) |
| `/openapi.json` | OpenAPI schema |

## Configuration

All settings are configurable via environment variables:

### Crawler Settings
- `MAX_CONCURRENT_REQUESTS`: Number of simultaneous page fetches (default: 5)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 30)
- `DEFAULT_MAX_PAGES`: Default pages to crawl (default: 50)
- `MAX_ALLOWED_PAGES`: Maximum allowed pages (default: 500)

### HTTP Client Settings
- `USER_AGENT`: Custom User-Agent header
- `MAX_RETRIES`: Retry attempts for failed requests
- `RETRY_DELAY`: Delay between retries (seconds)

### Content Extraction
- `CONTENT_SNIPPET_LENGTH`: Character limit for content snippets
- `MAX_CONTENT_LENGTH`: Maximum content per page

See `.env.example` for complete configuration.

## Performance Characteristics

### Speed
- Typical crawl of 50 pages: 10-30 seconds
- Concurrent fetching with asyncio
- Configurable concurrency limits

### Scalability
- Stateless design - horizontally scalable
- Async I/O for efficient resource usage
- Containerized for easy deployment

### Reliability
- Comprehensive error handling
- Timeout protection
- Graceful degradation on failures
- Error tracking and reporting

## Request/Response Format

### Request Example
```json
{
  "seed_url": "https://example.com",
  "max_pages": 50,
  "follow_external_links": false
}
```

### Response Example
```json
{
  "success": true,
  "base_url": "https://example.com",
  "total_pages_crawled": 5,
  "total_pages_requested": 10,
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "Example Page",
      "text_content": "Content here...",
      "content_snippet": "Content here...",
      "images": [
        {
          "url": "https://example.com/image.jpg",
          "alt_text": "Example"
        }
      ],
      "images_count": 1,
      "crawl_timestamp": "2024-01-12T10:30:45Z"
    }
  ],
  "errors": [],
  "crawl_duration_seconds": 12.5
}
```

## Docker Support

### Build
```bash
docker build -t crawler-service:latest .
```

### Run
```bash
docker run -p 8001:8001 crawler-service:latest
```

### Docker Compose
```bash
docker-compose up --build
```

## Integration Points

### Incoming Dependencies
- None - service is independent

### Outgoing Dependencies
- External websites (HTTP GET requests)

### Service Communication
- RESTful HTTP/JSON API
- Compatible with any HTTP client
- Can be called from other microservices

## Monitoring & Observability

### Health Endpoints
- `/health` - Quick health check
- `/api/v1/crawler/health` - Crawler-specific health
- `/status` - Detailed service status

### Logging
- Structured logging with timestamps
- Configurable log levels
- Error tracking per crawl

### Metrics (Can be added)
- Crawl duration
- Pages crawled
- Error rates
- Concurrency usage

## Error Handling

### Handled Errors
- Network timeouts
- HTTP error responses (404, 500, etc.)
- Connection failures
- Malformed HTML
- Invalid URLs
- Request exceptions

### Error Reporting
All errors are collected and returned in the response for visibility and debugging.

## Future Enhancements

1. **Database Integration**: Store crawl results and history
2. **Redis Caching**: Cache crawl results
3. **Advanced Parsing**: Support for JavaScript-rendered content
4. **Metrics & Monitoring**: Prometheus metrics export
5. **Advanced Filtering**: CSS selectors for content extraction
6. **Scheduled Crawls**: Background task scheduling
7. **Rate Limiting**: Per-IP request limiting
8. **Authentication**: API key authentication
9. **Webhooks**: Callback notifications on crawl completion
10. **Proxy Support**: Crawling through proxies

## Environment Setup

### Local Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Docker
```bash
docker-compose up --build
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app

# Async tests
pytest -v -s
```

## Related Services

This service is part of a larger microservice ecosystem:
- **Authentication Service**: User identity management
- **App Service**: Core application logic
- **Customer Service**: Customer data management
- **Webhook Service**: Event handling and webhooks
- **Crawler Service**: Web crawling (this service)

## Documentation Links

- **API Documentation**: http://localhost:8001/docs
- **README**: See README.md
- **Configuration**: See .env.example

## Troubleshooting

### Service Won't Start
- Check Python version: 3.11+
- Verify port 8001 is not in use
- Check environment variables

### Crawling Fails
- Verify seed URL is valid and accessible
- Check network connectivity
- Review logs for specific error messages

### High Memory Usage
- Reduce `MAX_CONCURRENT_REQUESTS`
- Reduce `DEFAULT_MAX_PAGES`
- Reduce `MAX_CONTENT_LENGTH`

## Support & Maintenance

For issues or questions:
1. Check logs for error details
2. Review README.md for usage examples
3. Check .env.example for configuration options
4. Consult API documentation at `/docs`
