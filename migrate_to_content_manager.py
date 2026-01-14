"""
Migration Script: Rename crawled_content to content_manager
This script helps migrate from the old crawled_content table to the new content_manager table
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    exit(1)

print(f"Connecting to database...")
engine = create_engine(DATABASE_URL)

def migrate():
    """Migrate from crawled_content to content_manager"""
    
    with engine.begin() as conn:
        # Check if old table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'crawled_content'
            );
        """))
        old_table_exists = result.scalar()
        
        # Check if new table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'content_manager'
            );
        """))
        new_table_exists = result.scalar()
        
        print(f"Old table (crawled_content) exists: {old_table_exists}")
        print(f"New table (content_manager) exists: {new_table_exists}")
        
        if old_table_exists and not new_table_exists:
            print("\nMigrating data from crawled_content to content_manager...")
            
            # Create new table with all the new fields
            print("Creating content_manager table...")
            conn.execute(text("""
                CREATE TABLE content_manager (
                    id UUID PRIMARY KEY,
                    url VARCHAR(2048) UNIQUE NOT NULL,
                    base_url VARCHAR(512) NOT NULL,
                    domain VARCHAR(255) NOT NULL,
                    title VARCHAR(512),
                    description TEXT,
                    content_type VARCHAR(100) DEFAULT 'text/html',
                    language VARCHAR(10),
                    text_content TEXT NOT NULL,
                    content_snippet TEXT,
                    raw_html TEXT,
                    images JSONB DEFAULT '[]'::jsonb,
                    images_count INTEGER DEFAULT 0,
                    videos JSONB DEFAULT '[]'::jsonb,
                    links JSONB DEFAULT '[]'::jsonb,
                    meta_tags JSONB DEFAULT '{}'::jsonb,
                    keywords JSONB DEFAULT '[]'::jsonb,
                    author VARCHAR(255),
                    word_count INTEGER DEFAULT 0,
                    content_hash VARCHAR(64),
                    quality_score INTEGER DEFAULT 0,
                    crawl_status VARCHAR(50) DEFAULT 'completed',
                    crawl_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_updated TIMESTAMP WITH TIME ZONE,
                    crawl_depth INTEGER DEFAULT 0,
                    http_status_code INTEGER,
                    response_time_ms INTEGER,
                    embedding vector(384),
                    embedding_model VARCHAR(100),
                    is_processed BOOLEAN DEFAULT FALSE,
                    is_indexed BOOLEAN DEFAULT FALSE,
                    needs_reprocessing BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    custom_metadata JSONB DEFAULT '{}'::jsonb
                );
            """))
            
            # Create indexes
            print("Creating indexes...")
            conn.execute(text("CREATE INDEX idx_url_hash ON content_manager(url);"))
            conn.execute(text("CREATE INDEX idx_base_url ON content_manager(base_url);"))
            conn.execute(text("CREATE INDEX idx_domain ON content_manager(domain);"))
            conn.execute(text("CREATE INDEX idx_content_type ON content_manager(content_type);"))
            conn.execute(text("CREATE INDEX idx_crawl_status ON content_manager(crawl_status);"))
            conn.execute(text("CREATE INDEX idx_crawl_timestamp ON content_manager(crawl_timestamp);"))
            conn.execute(text("CREATE INDEX idx_is_processed ON content_manager(is_processed);"))
            conn.execute(text("CREATE INDEX idx_content_hash ON content_manager(content_hash);"))
            conn.execute(text("CREATE INDEX idx_domain_status ON content_manager(domain, crawl_status);"))
            conn.execute(text("CREATE INDEX idx_timestamp_status ON content_manager(crawl_timestamp, crawl_status);"))
            
            # Migrate data
            print("Migrating data...")
            conn.execute(text("""
                INSERT INTO content_manager (
                    id, url, base_url, domain, title, text_content, 
                    content_snippet, images_count, crawl_timestamp
                )
                SELECT 
                    id, 
                    url, 
                    base_url,
                    SUBSTRING(base_url FROM '://([^/]+)') as domain,
                    title, 
                    text_content, 
                    content_snippet,
                    CAST(images_count AS INTEGER),
                    crawl_timestamp
                FROM crawled_content;
            """))
            
            result = conn.execute(text("SELECT COUNT(*) FROM content_manager;"))
            count = result.scalar()
            print(f"Migrated {count} records successfully!")
            
            # Optionally drop old table (commented out for safety)
            # print("Dropping old table...")
            # conn.execute(text("DROP TABLE crawled_content;"))
            print("\nMigration complete! Old table 'crawled_content' is still present.")
            print("You can manually drop it after verifying the migration: DROP TABLE crawled_content;")
            
        elif new_table_exists:
            print("\nNew table 'content_manager' already exists. No migration needed.")
            if old_table_exists:
                print("Old table 'crawled_content' still exists. You may want to drop it manually.")
        else:
            print("\nNo migration needed. Tables will be created on first run.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"ERROR during migration: {e}")
        import traceback
        traceback.print_exc()
