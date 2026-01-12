# Crawler Microservice

A high-performance web crawler and scraper microservice built with FastAPI, BeautifulSoup4, and AsyncIO. Similar to Apify, this service provides a structured API for crawling websites, extracting content, and collecting metadata.

## 🚀 Features

- **Recursive Web Crawling** - Follow links within the same domain automatically
- **Domain Boundary Protection** - Automatically stays within the base domain
- **Content Extraction** - Extract titles, text content, and image URLs
- **Asynchronous Processing** - Concurrent page fetching with configurable limits
- **Error Handling** - Graceful handling of timeouts, 404s, and network errors
- **Batch Operations** - Crawl multiple domains in a single request
- **Structured Output** - Clean JSON responses with comprehensive metadata
- **Rate Limiting** - Configurable concurrency and retry logic

## 🏗️ Architecture

The service follows a clean layered architecture pattern:

```
app/
├── api/                      # HTTP Layer
│   └── v1/
│       └── endpoints/
│           └── crawler.py    # API route handlers
├── core/                     # Cross-cutting concerns
│   └── config.py            # Configuration and settings
├── services/                 # Business Logic Layer
│   └── crawler.py           # Crawling and scraping logic
├── schemas/                  # Data Validation
│   └── crawler.py           # Pydantic request/response models
├── models/                   # Data Models
└── main.py                  # FastAPI application setup
```

## 📋 Requirements

- Python 3.11+
- FastAPI
- Uvicorn
- httpx (async HTTP client)
- BeautifulSoup4 (HTML parsing)
- Pydantic (data validation)

See `requirements.txt` for complete dependencies.

## 📦 Installation

### Local Development

```bash
# Clone the repository
cd crowler-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t crawler-service .
docker run -p 8001:8001 crawler-service
```

The service will be available at `http://localhost:8001`

## 🔌 API Endpoints

### Health Check
```http
GET /api/v1/crawler/health
```

Returns:
```json
{
  "status": "healthy",
  "service": "crawler-microservice"
}
```

### Basic Crawl
```http
POST /api/v1/crawler/crawl
Content-Type: application/json

{
  "seed_url": "https://example.com",
  "max_pages": 50,
  "follow_external_links": false
}
```

**Parameters:**
- `seed_url` (required, HttpUrl): Starting URL to crawl
- `max_pages` (optional, int): Maximum pages to crawl (1-500, default: 50)
- `follow_external_links` (optional, bool): Follow links outside base domain (default: false)

**Response:**
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
      "text_content": "Full page content here...",
      "content_snippet": "Full page content here...",
      "images": [
        {
          "url": "https://example.com/image.jpg",
          "alt_text": "Example image"
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

### Batch Crawl
```http
POST /api/v1/crawler/crawl/batch
Content-Type: application/json

[
  {
    "seed_url": "https://example1.com",
    "max_pages": 20
  },
  {
    "seed_url": "https://example2.com",
    "max_pages": 30
  }
]
```

**Constraints:**
- Maximum 10 URLs per batch request
- Each crawl is independent with its own domain boundary

**Response:**
```json
{
  "batch_results": {
    "https://example1.com": {
      "success": true,
      "data": { ... }
    },
    "https://example2.com": {
      "success": true,
      "data": { ... }
    }
  }
}
```

### Domain Info
```http
GET /api/v1/crawler/crawl/domains/{domain}
```

Returns information about a domain's crawl status.

## 🔧 Configuration

Configuration is managed through environment variables in `.env` or via `docker-compose.yml`:

```env
# Application
APP_NAME=Crawler Microservice
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8001

# Crawler Settings
MAX_CONCURRENT_REQUESTS=5          # Concurrent page fetches
REQUEST_TIMEOUT=30                 # Request timeout in seconds
DEFAULT_MAX_PAGES=50               # Default page limit
MAX_ALLOWED_PAGES=500              # Maximum allowed pages

# HTTP Client
USER_AGENT=CrawlerBot/1.0
MAX_RETRIES=3
RETRY_DELAY=2

# Content Extraction
CONTENT_SNIPPET_LENGTH=200         # Character limit for snippet
MAX_CONTENT_LENGTH=10000           # Character limit per page
```

## 📊 How It Works

### Crawling Algorithm

1. **Initialize**: Start with a seed URL, extract base domain
2. **Queue Management**: Add seed URL to crawl queue, mark as visited
3. **Concurrent Fetching**: Fetch multiple pages simultaneously (within concurrency limit)
4. **Parsing**: Parse HTML with BeautifulSoup, extract:
   - Page title
   - Text content
   - Image URLs with alt text
   - Internal links
5. **Link Discovery**: Add new, unvisited links from same domain to queue
6. **Rate Control**: Small delays between batches to avoid overwhelming server
7. **Boundary Check**: All discovered links checked to stay within base domain
8. **Response**: Return structured data with all crawled pages and metadata

### Key Components

#### CrawlerService (`app/services/crawler.py`)
- Core crawling logic with async operations
- Manages visited URLs, crawl queue, and batch processing
- Handles URL normalization and domain boundary checking
- Parses HTML and extracts content, images, and links
- Error tracking and graceful failure handling

#### API Endpoints (`app/api/v1/endpoints/crawler.py`)
- RESTful interface for crawling operations
- Request validation using Pydantic schemas
- Comprehensive error handling and HTTP status codes
- Support for single and batch crawling

#### Schemas (`app/schemas/crawler.py`)
- `CrawlRequest`: Validates input parameters
- `PageContent`: Structure for extracted page data
- `ImageData`: Image information with alt text
- `CrawlResponse`: Complete crawl results
- `CrawlErrorResponse`: Standardized error format

## 🛡️ Error Handling

The service handles various error conditions gracefully:

- **Timeout Errors**: Request timeout handling with configurable duration
- **HTTP Errors**: 404 and other HTTP error tracking
- **Network Errors**: Connection failures and DNS resolution issues
- **Parsing Errors**: Malformed HTML or missing elements
- **Invalid URLs**: URL validation and normalization

All errors are collected and returned in the response for visibility.

## 🚦 Rate Limiting & Concurrency

### Concurrency Control
- Configurable `MAX_CONCURRENT_REQUESTS` (default: 5)
- Prevents overwhelming target servers
- Batch processing with inter-batch delays

### Request Timeouts
- Configurable `REQUEST_TIMEOUT` (default: 30 seconds)
- Prevents hanging requests
- Graceful timeout error handling

### Retry Logic
- Configurable `MAX_RETRIES` (default: 3)
- Exponential backoff with `RETRY_DELAY`
- Automatic retry on transient failures

## 📈 Performance Characteristics

- **Async Processing**: Uses Python's asyncio for efficient concurrent operations
- **Memory Efficient**: Processes pages in batches, doesn't load all at once
- **Scalable**: Concurrency limits prevent resource exhaustion
- **Fast**: Typical crawl of 50 pages completes in 10-30 seconds

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Run async tests
pytest -v -s tests/
```

## 📝 Example Usage

### Using Python Requests

```python
import requests
import json

# Basic crawl
response = requests.post('http://localhost:8001/api/v1/crawler/crawl', json={
    'seed_url': 'https://example.com',
    'max_pages': 20
})

crawl_data = response.json()
print(f"Crawled {crawl_data['total_pages_crawled']} pages")
print(f"Duration: {crawl_data['crawl_duration_seconds']:.2f} seconds")

# Batch crawl
batch_response = requests.post('http://localhost:8001/api/v1/crawler/crawl/batch', json=[
    {'seed_url': 'https://example1.com', 'max_pages': 15},
    {'seed_url': 'https://example2.com', 'max_pages': 20}
])

batch_data = batch_response.json()
for url, result in batch_data['batch_results'].items():
    if result['success']:
        print(f"✓ {url}: {result['data']['total_pages_crawled']} pages")
    else:
        print(f"✗ {url}: {result['error']}")
```

### Using cURL

```bash
# Health check
curl http://localhost:8001/api/v1/crawler/health

# Single crawl
curl -X POST http://localhost:8001/api/v1/crawler/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "seed_url": "https://example.com",
    "max_pages": 20
  }'

# Batch crawl
curl -X POST http://localhost:8001/api/v1/crawler/crawl/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"seed_url": "https://example1.com", "max_pages": 15},
    {"seed_url": "https://example2.com", "max_pages": 20}
  ]'
```

## 📚 Documentation

- **Interactive API Docs**: Available at `http://localhost:8001/docs` (Swagger UI)
- **ReDoc Documentation**: Available at `http://localhost:8001/redoc`
- **OpenAPI Schema**: Available at `http://localhost:8001/openapi.json`

## 🔄 Integration with Other Services

The crawler service is designed to work as a microservice in a distributed architecture:

- **Async Operations**: Non-blocking API suitable for event-driven architectures
- **Stateless Design**: Can be scaled horizontally
- **Docker Ready**: Containerized for easy deployment
- **Clean API**: RESTful interface for easy integration
- **Error Tracking**: Comprehensive error reporting for monitoring

## 🚀 Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
Create a deployment YAML:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crawler-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crawler
  template:
    metadata:
      labels:
        app: crawler
    spec:
      containers:
      - name: crawler
        image: crawler-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: MAX_CONCURRENT_REQUESTS
          value: "5"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- BeautifulSoup4 for HTML parsing
- httpx for async HTTP operations
- Pydantic for data validation

## 📞 Support

For issues, questions, or suggestions, please open an issue on the repository or contact the development team.
