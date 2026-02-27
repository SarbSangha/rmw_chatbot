# TODO: Fix Web Search Fallback and Latency Issues - COMPLETED

## Issues Fixed:
1. **Web search returns empty** when exact query matches aren't found on the website
2. **Latency issues** due to repeated scraping and synchronous operations

## Changes Made:

### 1. app/utils/web_scraper.py ✅ COMPLETED
- [x] Modified `search_website` function to fall back to full website content when no specific matches are found
- [x] Added caching for website content to reduce latency on subsequent requests
- [x] Reduced max_pages for faster initial search (5 pages instead of 10)

### 2. app/services/chat_service.py  
- [x] Already passes web_context to RAG graph when available

## Summary:
- When `search_website` returns empty, it now calls `get_website_content` to get full scraped content
- Website content is cached globally to avoid re-scraping on subsequent requests
- Reduced max_pages from 10 to 5 for faster scraping
