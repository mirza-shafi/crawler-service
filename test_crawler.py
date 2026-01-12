"""
Test Script - Quick test of the Crawler API

Run this script to test the crawler service locally
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8001"


def test_health():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")


def test_crawler_health():
    """Test crawler health check"""
    print("🔍 Testing crawler health...")
    response = requests.get(f"{BASE_URL}/api/v1/crawler/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")


def test_single_crawl(url: str = "https://example.com", max_pages: int = 5):
    """Test single website crawl"""
    print(f"🕷️ Testing single crawl of {url}...")
    
    data = {
        "seed_url": url,
        "max_pages": max_pages,
        "follow_external_links": False
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/crawler/crawl", json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Crawled {result['total_pages_crawled']} pages")
        print(f"Duration: {result['crawl_duration_seconds']:.2f} seconds")
        print(f"Errors: {len(result['errors'])}")
        
        # Show first page
        if result['pages']:
            first_page = result['pages'][0]
            print(f"\nFirst page: {first_page['url']}")
            print(f"Title: {first_page['title']}")
            print(f"Images: {first_page['images_count']}")
            print(f"Content snippet: {first_page['content_snippet'][:100]}...")
    else:
        print(f"❌ Error: {response.text}")
    
    print()


def test_batch_crawl():
    """Test batch crawl of multiple websites"""
    print("🕷️ Testing batch crawl...")
    
    data = [
        {"seed_url": "https://example.com", "max_pages": 3},
        {"seed_url": "https://httpbin.org", "max_pages": 3}
    ]
    
    response = requests.post(f"{BASE_URL}/api/v1/crawler/crawl/batch", json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Batch crawl completed!")
        
        for url, crawl_result in result['batch_results'].items():
            if crawl_result['success']:
                pages = crawl_result['data']['total_pages_crawled']
                print(f"  ✓ {url}: {pages} pages")
            else:
                print(f"  ✗ {url}: {crawl_result['error']}")
    else:
        print(f"❌ Error: {response.text}")
    
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("Crawler Microservice - Test Script")
    print("=" * 60)
    print()
    
    try:
        # Basic health checks
        test_health()
        test_crawler_health()
        
        # Crawl tests
        test_single_crawl("https://example.com", max_pages=5)
        test_batch_crawl()
        
        print("=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to the service.")
        print("Make sure the service is running on http://localhost:8001")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
