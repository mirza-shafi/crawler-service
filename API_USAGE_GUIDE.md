# Crawler API - Usage Guide

Complete guide for using the Crawler Microservice API.

## Table of Contents
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
- [Request Examples](#request-examples)
- [Response Structure](#response-structure)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Code Examples](#code-examples)

## Getting Started

The Crawler API provides a simple HTTP interface for crawling and scraping websites. No API key or authentication is required by default.

### Prerequisites
- Service running on port 8001
- HTTP client (curl, requests, etc.)
- Valid URLs to crawl

## Authentication

**Note**: Current version does not require authentication. Future versions may include API key authentication.

## Base URL

```
http://localhost:8001
```

For production:
```
https://crawler-api.yourdomain.com
```

## Endpoints

### Health & Status

#### 1. Root Information
```http
GET /
```

**Response:**
```json
{
  "service": "Crawler Microservice",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/api/v1/crawler/health"
}
```

#### 2. Health Check
```http
GET /health
GET /api/v1/crawler/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Crawler Microservice"
}
```

#### 3. Service Status
```http
GET /status
```

**Response:**
```json
{
  "service": "Crawler Microservice",
  "version": "1.0.0",
  "status": "running",
  "config": {
    "max_concurrent_requests": 5,
    "request_timeout": 30,
    "default_max_pages": 50,
    "max_allowed_pages": 500
  }
}
```

### Crawling Operations

#### 4. Single Website Crawl
```http
POST /api/v1/crawler/crawl
Content-Type: application/json
```

**Request Body:**
```json
{
  "seed_url": "https://example.com",
  "max_pages": 50,
  "follow_external_links": false
}
```

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| seed_url | HttpUrl | Yes | - | Starting URL to crawl |
| max_pages | int | No | 50 | Max pages (1-500) |
| follow_external_links | bool | No | false | Follow external domains |

**Response:** See [Crawl Response Structure](#crawl-response-structure)

#### 5. Batch Website Crawl
```http
POST /api/v1/crawler/crawl/batch
Content-Type: application/json
```

**Request Body:**
```json
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
- Maximum 10 URLs per batch
- Each crawl is independent

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

#### 6. Domain Information
```http
GET /api/v1/crawler/crawl/domains/{domain}
```

**Response:**
```json
{
  "domain": "example.com",
  "message": "Domain crawl information not stored (stateless service)",
  "note": "For persistent storage, integrate with a database or cache"
}
```

## Request Examples

### Using cURL

#### Basic Crawl
```bash
curl -X POST http://localhost:8001/api/v1/crawler/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "seed_url": "https://example.com",
    "max_pages": 20
  }'
```

#### With All Parameters
```bash
curl -X POST http://localhost:8001/api/v1/crawler/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "seed_url": "https://blog.example.com",
    "max_pages": 100,
    "follow_external_links": false
  }'
```

#### Batch Crawl
```bash
curl -X POST http://localhost:8001/api/v1/crawler/crawl/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"seed_url": "https://example1.com", "max_pages": 15},
    {"seed_url": "https://example2.com", "max_pages": 20}
  ]'
```

### Using HTTPie

```bash
# Basic crawl
http POST localhost:8001/api/v1/crawler/crawl \
  seed_url=https://example.com \
  max_pages:=20

# Batch crawl
http POST localhost:8001/api/v1/crawler/crawl/batch < batch_request.json
```

## Response Structure

### Crawl Response Structure

```json
{
  "success": true,
  "base_url": "https://example.com",
  "total_pages_crawled": 5,
  "total_pages_requested": 10,
  "pages": [
    {
      "url": "https://example.com/page1",
      "title": "Page Title",
      "text_content": "Full text content of the page...",
      "content_snippet": "Short snippet of content...",
      "images": [
        {
          "url": "https://example.com/image.jpg",
          "alt_text": "Image description"
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

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether crawl completed successfully |
| base_url | string | Starting URL that was crawled |
| total_pages_crawled | integer | Successfully crawled pages |
| total_pages_requested | integer | Total pages visited/attempted |
| pages | array | List of PageContent objects |
| errors | array | List of error messages encountered |
| crawl_duration_seconds | float | Total time taken |

### Page Content Structure

| Field | Type | Description |
|-------|------|-------------|
| url | string | Page URL |
| title | string | Page title (from `<title>` tag) |
| text_content | string | Full extracted text content |
| content_snippet | string | Short snippet (200 chars) |
| images | array | List of ImageData objects |
| images_count | integer | Total number of images |
| crawl_timestamp | string | ISO 8601 timestamp |

### Image Data Structure

| Field | Type | Description |
|-------|------|-------------|
| url | string | Image source URL |
| alt_text | string | Image alt text (may be null) |

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found |
| 422 | Unprocessable Entity (validation error) |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Common Errors

#### Invalid URL
```json
{
  "detail": "Invalid URL format"
}
```

#### Max Pages Exceeded
```json
{
  "detail": "max_pages must be between 1 and 500"
}
```

#### Network Error
The crawl may succeed but include errors in the response:
```json
{
  "success": true,
  "errors": [
    "Timeout while fetching https://example.com/slow-page",
    "HTTP 404 for https://example.com/not-found"
  ]
}
```

## Best Practices

### 1. Respect Rate Limits
```python
import time

urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

for url in urls:
    crawl(url)
    time.sleep(5)  # Wait between requests
```

### 2. Use Appropriate max_pages
```python
# For small sites
crawl(seed_url="https://small-site.com", max_pages=10)

# For large sites
crawl(seed_url="https://large-site.com", max_pages=100)
```

### 3. Handle Errors Gracefully
```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
    
    if not result['success']:
        print(f"Crawl had errors: {result['errors']}")
except requests.RequestException as e:
    print(f"Request failed: {e}")
```

### 4. Process Results Incrementally
```python
result = crawl(seed_url, max_pages=100)

for page in result['pages']:
    process_page(page)  # Process one at a time
    save_to_database(page)
```

### 5. Use Batch Operations Wisely
```python
# Good: Small batch
batch = [
    {"seed_url": "https://site1.com", "max_pages": 20},
    {"seed_url": "https://site2.com", "max_pages": 20}
]

# Avoid: Too many or too large
batch = [
    {"seed_url": f"https://site{i}.com", "max_pages": 500}
    for i in range(10)
]  # This may timeout or fail
```

## Code Examples

### Python with requests

```python
import requests
import json

BASE_URL = "http://localhost:8001/api/v1/crawler"

def crawl_website(seed_url: str, max_pages: int = 50):
    """Crawl a single website"""
    payload = {
        "seed_url": seed_url,
        "max_pages": max_pages,
        "follow_external_links": False
    }
    
    response = requests.post(f"{BASE_URL}/crawl", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Crawled {result['total_pages_crawled']} pages")
        print(f"Duration: {result['crawl_duration_seconds']:.2f}s")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def batch_crawl(urls: list):
    """Crawl multiple websites"""
    requests_data = [
        {"seed_url": url, "max_pages": 20}
        for url in urls
    ]
    
    response = requests.post(f"{BASE_URL}/crawl/batch", json=requests_data)
    
    if response.status_code == 200:
        result = response.json()
        for url, crawl_result in result['batch_results'].items():
            if crawl_result['success']:
                pages = crawl_result['data']['total_pages_crawled']
                print(f"✓ {url}: {pages} pages")
            else:
                print(f"✗ {url}: {crawl_result['error']}")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        return None

def extract_images(pages):
    """Extract all images from crawl results"""
    all_images = []
    for page in pages:
        for image in page['images']:
            all_images.append({
                'page_url': page['url'],
                'image_url': image['url'],
                'alt_text': image.get('alt_text')
            })
    return all_images

# Usage
if __name__ == "__main__":
    # Single crawl
    result = crawl_website("https://example.com", max_pages=30)
    
    if result:
        # Extract images
        images = extract_images(result['pages'])
        print(f"\nTotal images found: {len(images)}")
        
    # Batch crawl
    urls = ["https://example1.com", "https://example2.com"]
    batch_crawl(urls)
```

### JavaScript/Node.js with axios

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8001/api/v1/crawler';

async function crawlWebsite(seedUrl, maxPages = 50) {
    try {
        const response = await axios.post(`${BASE_URL}/crawl`, {
            seed_url: seedUrl,
            max_pages: maxPages,
            follow_external_links: false
        });
        
        const result = response.data;
        console.log(`✅ Crawled ${result.total_pages_crawled} pages`);
        console.log(`Duration: ${result.crawl_duration_seconds.toFixed(2)}s`);
        return result;
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        if (error.response) {
            console.error(error.response.data);
        }
        return null;
    }
}

async function batchCrawl(urls) {
    const requests = urls.map(url => ({
        seed_url: url,
        max_pages: 20
    }));
    
    try {
        const response = await axios.post(`${BASE_URL}/crawl/batch`, requests);
        const result = response.data;
        
        for (const [url, crawlResult] of Object.entries(result.batch_results)) {
            if (crawlResult.success) {
                const pages = crawlResult.data.total_pages_crawled;
                console.log(`✓ ${url}: ${pages} pages`);
            } else {
                console.log(`✗ ${url}: ${crawlResult.error}`);
            }
        }
        
        return result;
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        return null;
    }
}

// Usage
(async () => {
    // Single crawl
    const result = await crawlWebsite('https://example.com', 30);
    
    // Batch crawl
    const urls = ['https://example1.com', 'https://example2.com'];
    await batchCrawl(urls);
})();
```

### Go with net/http

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

const BaseURL = "http://localhost:8001/api/v1/crawler"

type CrawlRequest struct {
    SeedURL             string `json:"seed_url"`
    MaxPages            int    `json:"max_pages"`
    FollowExternalLinks bool   `json:"follow_external_links"`
}

type CrawlResponse struct {
    Success              bool     `json:"success"`
    BaseURL              string   `json:"base_url"`
    TotalPagesCrawled    int      `json:"total_pages_crawled"`
    TotalPagesRequested  int      `json:"total_pages_requested"`
    Errors               []string `json:"errors"`
    CrawlDurationSeconds float64  `json:"crawl_duration_seconds"`
}

func crawlWebsite(seedURL string, maxPages int) (*CrawlResponse, error) {
    request := CrawlRequest{
        SeedURL:             seedURL,
        MaxPages:            maxPages,
        FollowExternalLinks: false,
    }
    
    jsonData, err := json.Marshal(request)
    if err != nil {
        return nil, err
    }
    
    resp, err := http.Post(
        fmt.Sprintf("%s/crawl", BaseURL),
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result CrawlResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }
    
    return &result, nil
}

func main() {
    result, err := crawlWebsite("https://example.com", 30)
    if err != nil {
        fmt.Printf("❌ Error: %v\n", err)
        return
    }
    
    fmt.Printf("✅ Crawled %d pages\n", result.TotalPagesCrawled)
    fmt.Printf("Duration: %.2fs\n", result.CrawlDurationSeconds)
}
```

## Advanced Usage

### Parallel Processing

```python
import concurrent.futures
import requests

def crawl_one(url):
    response = requests.post(
        "http://localhost:8001/api/v1/crawler/crawl",
        json={"seed_url": url, "max_pages": 20}
    )
    return response.json()

urls = ["https://site1.com", "https://site2.com", "https://site3.com"]

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(crawl_one, urls))

for url, result in zip(urls, results):
    print(f"{url}: {result['total_pages_crawled']} pages")
```

### Custom Processing Pipeline

```python
def process_crawl_results(seed_url, max_pages):
    # 1. Crawl
    result = crawl_website(seed_url, max_pages)
    
    if not result:
        return None
    
    # 2. Extract structured data
    pages_data = []
    for page in result['pages']:
        pages_data.append({
            'url': page['url'],
            'title': page['title'],
            'word_count': len(page['text_content'].split()),
            'image_count': page['images_count'],
            'timestamp': page['crawl_timestamp']
        })
    
    # 3. Save to database
    save_to_database(pages_data)
    
    # 4. Generate report
    return {
        'total_pages': len(pages_data),
        'total_words': sum(p['word_count'] for p in pages_data),
        'total_images': sum(p['image_count'] for p in pages_data)
    }
```

## Documentation

- **Interactive API Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI Schema**: http://localhost:8001/openapi.json

## Support

For issues or questions:
1. Check the [README](README.md)
2. Review [microservice_info.md](microservice_info.md)
3. Consult the interactive API documentation at `/docs`
4. Check logs for detailed error messages
