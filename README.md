# Reddit Opportunity Scanner

## Overview

A Flexus bot that scans Reddit subreddits to identify business opportunities by analyzing user complaints, pain points, and unmet needs. It fetches posts and comments, cleans the noisy JSON data, and uses an LLM to extract actionable micro-SaaS ideas.

## Problem Statement

Entrepreneurs and product builders need to identify real market problems that people are willing to pay to solve. Reddit communities contain valuable signals—recurring complaints, feature requests, and workarounds—but the data is buried in noise and requires manual analysis.

## Solution

This bot automates the discovery process by:
1. Fetching recent posts from specified subreddits
2. Extracting and cleaning relevant content (titles, post bodies, comments)
3. Analyzing the text with an LLM trained to spot "hair-on-fire" problems
4. Producing a structured report with business opportunity recommendations

## User Interaction

- **Platform**: Chat interface in Flexus
- **Trigger**: On-demand (user provides list of subreddits)
- **Input**: User message with subreddit names, e.g., "Scan wordpress, saas, copywriting"
- **Output**: Markdown report with opportunity table and top recommendation

## Bot Behavior

### Workflow

1. **Parse Request**: Extract subreddit names from user message
2. **Fetch Data**: For each subreddit:
   - Request `https://www.reddit.com/r/{subreddit}/new.json?limit=50`
   - Use custom User-Agent header (required by Reddit)
   - Filter posts with upvotes >= 0
   - Select top 30 posts by engagement (upvotes + comments)
3. **Fetch Comments**: For each of the top 30 posts:
   - Request `https://www.reddit.com/r/{subreddit}/comments/{post_id}.json`
   - Extract top-level and nested comments
4. **Clean Data**: Remove metadata, keep only:
   - Post title
   - Post body (selftext)
   - Comment bodies
5. **Rate Limiting**: Sleep 2-3 seconds between requests to avoid IP ban
6. **Analyze**: Send cleaned text to LLM with system prompt (see below)
7. **Report**: Return formatted markdown table to user

### Data Filters

- Minimum upvotes: 0 (exclude negative)
- Post limit per subreddit: 50
- Comment depth: All levels (top-level and nested)
- Focus posts: Top 30 by engagement (upvotes + comment_count)

### LLM Configuration

- **Model**: GPT-4o-mini or Claude Haiku (cost-optimized)
- **System Prompt**: Instructs LLM to act as a "Product Detective" looking for:
  - Recurring complaints
  - Feature gaps ("Is there a tool for X?")
  - Inefficient workarounds
  - Competitor weaknesses
  - Willingness to pay signals ("I would pay for...")
- **Output Format**: Markdown table with columns:
  - Pain Point Summary
  - Evidence (quotes)
  - Intensity (High/Med)
  - Proposed Solution
  - Monetization Idea
- **Gold Nugget**: Single best opportunity with 2-sentence justification

### Error Handling

- Invalid subreddit: Skip and log warning
- Rate limit hit: Exponential backoff and retry
- Empty results: Inform user "No actionable opportunities found"

## Technical Requirements

### External Dependencies

- **Reddit API**: Public JSON endpoints (no auth required)
  - Must include `User-Agent: Mozilla/5.0 (compatible; RedditScanner/1.0)`
- **LLM API**: OpenAI or Anthropic
  - Requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable

### Python Libraries

- `requests` (HTTP)
- `asyncio` (rate limiting)
- `openai` or `anthropic` (LLM client)
- `flexus-client-kit` (bot framework)

### Rate Limits

- Reddit: ~60 requests/minute (unofficial)
- Strategy: 2-second delay between requests

## Installation

1. Set environment variable:
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
2. Run install script:
   ```bash
   python -m idea_bot.reddit_opportunity_scanner_install --ws=<workspace_id>
   ```

## Example Usage

**User Input:**
```
Scan wordpress, woocommerce, shopify
```

**Bot Output:**
```markdown
# Reddit Opportunity Analysis

Scanned 3 subreddits (150 posts, 847 comments)

| Pain Point Summary | Evidence (Quotes/Context) | Intensity | Proposed Micro-SaaS/Solution | Monetization Idea |
| :--- | :--- | :--- | :--- | :--- |
| Media Library Chaos | "I have 5,000 images and can't filter by 'unused'. It's a nightmare cleaning up the site." | High | A "Deep Clean" plugin that identifies orphaned media and compresses remaining files safely. | Freemium (Scan for free, pay $19 to clean) |
| Client Handoff Confusion | "My clients break the site immediately. I need to hide the dashboard menus." | Med | A "Client Mode" interface plugin that simplifies the WP Admin to just 3 buttons. | $49 Lifetime License (Agency focus) |

## The Gold Nugget

The "Client Mode" plugin is the strongest opportunity. It targets agencies (who have money) and solves a recurring headache (clients breaking sites), making it a high-value B2B tool.
```

## Success Metrics

- Time to generate report: < 2 minutes for 3 subreddits
- Relevance: 80%+ of identified opportunities should be actionable
- User satisfaction: Clear, concise output with no manual cleanup needed

## Future Enhancements

- Support for filtering by post flair (e.g., "Help", "Question")
- Historical tracking to identify trending pain points over time
- Competitor analysis (scan mentions of specific tools/products)
- Automated follow-up: monitor identified opportunities for validation signals