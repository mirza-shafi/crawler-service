#!/bin/bash
# Script to install and enable pgvector extension in PostgreSQL

set -e

echo "Installing pgvector extension..."

# Update and install build dependencies
apt-get update
apt-get install -y --no-install-recommends git build-essential postgresql-server-dev-15

# Clone and install pgvector
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Clean up
cd /
rm -rf /tmp/pgvector
apt-get remove -y git build-essential postgresql-server-dev-15
apt-get autoremove -y
apt-get clean
rm -rf /var/lib/apt/lists/*

# Enable the extension in the database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    SELECT * FROM pg_extension WHERE extname = 'vector';
EOSQL

echo "✓ pgvector extension installed and enabled successfully!"
