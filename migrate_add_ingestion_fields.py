"""
Migration script to add multi-source ingestion fields to content_manager table
"""

import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

async def migrate():
    """Add new columns for multi-source content ingestion"""
    
    # Create synchronous engine for migration
    engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))
    
    migrations = [
        # Add source_type column
        """
        ALTER TABLE content_manager 
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) DEFAULT 'url';
        """,
        
        # Add source_identifier column
        """
        ALTER TABLE content_manager 
        ADD COLUMN IF NOT EXISTS source_identifier VARCHAR(512);
        """,
        
        # Add file_metadata column
        """
        ALTER TABLE content_manager 
        ADD COLUMN IF NOT EXISTS file_metadata JSONB DEFAULT '{}'::jsonb;
        """,
        
        # Make url nullable
        """
        ALTER TABLE content_manager 
        ALTER COLUMN url DROP NOT NULL;
        """,
        
        # Make base_url nullable
        """
        ALTER TABLE content_manager 
        ALTER COLUMN base_url DROP NOT NULL;
        """,
        
        # Make domain nullable
        """
        ALTER TABLE content_manager 
        ALTER COLUMN domain DROP NOT NULL;
        """,
        
        # Add index on source_type
        """
        CREATE INDEX IF NOT EXISTS idx_source_type ON content_manager(source_type);
        """,
    ]
    
    try:
        with engine.connect() as conn:
            print("Starting migration...")
            
            for i, migration_sql in enumerate(migrations, 1):
                print(f"Running migration {i}/{len(migrations)}...")
                conn.execute(text(migration_sql))
                conn.commit()
                print(f"✓ Migration {i} completed")
            
            print("\n✅ All migrations completed successfully!")
            print("\nNew fields added:")
            print("  - source_type (VARCHAR)")
            print("  - source_identifier (VARCHAR)")
            print("  - file_metadata (JSONB)")
            print("\nUpdated fields:")
            print("  - url (now nullable)")
            print("  - base_url (now nullable)")
            print("  - domain (now nullable)")
            print("\nNew indexes:")
            print("  - idx_source_type")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
