#!/bin/bash

# Clean up all old parquet files
rm -rf *.parquet

# Run the scraper
uv run main.py

uv run backend/service/framework.py