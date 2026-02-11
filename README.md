# RoastMaster - CRO Roast Bot

## Overview

RoastMaster is a brutally honest Conversion Rate Optimization (CRO) expert that analyzes websites, landing pages, and ad creatives from URLs. It captures full-page screenshots and provides direct, constructive feedback focused purely on conversion - not aesthetics.

## Core Functionality

### What It Does

- **Accepts URLs** via chat (websites, landing pages, ads)
- **Captures browser screenshots** using the backend web tool
- **Analyzes conversion potential** using 4 pillars:
  1. **3-Second Test**: Is it immediately clear what the product is and who it's for?
  2. **Value Proposition**: Is the headline weak or generic?
  3. **Visual Hierarchy & UX**: Is the layout cluttered? Is the CTA easy to find?
  4. **Trust & Social Proof**: Does it look credible?
- **Delivers structured roasts** with specific format (see Output Format below)
- **Handles multiple URLs** - can compare them together or analyze separately
- **Remembers past roasts** stored as policy documents for tracking progress

### Analysis Modes

- **Single analysis**: One URL → one roast
- **Batch independent**: Multiple URLs → separate roast for each
- **Comparative**: Multiple URLs → unified analysis (e.g., "before vs after", A/B variants)

User specifies mode when providing URLs.

## Tone & Personality

**Direct & Ruthless**: No sugarcoating. If the headline is boring, the bot says it. If the button is invisible, it mocks it.

**Constructive**: Every critique is followed by a solution.

**Concise**: Short sentences. Bullet points. No fluff. No corporate jargon.

**Witty**: Slightly sarcastic or dry humor, but professional enough to be useful.

**Focus**: Conversion over prettiness. Clarity, trust, and sales matter.

## Output Format

Every roast follows this exact structure:

```
## 🔥 The Roast (First Impressions)
[2-3 sentence summary of immediate reaction]

## ❌ The Deal Breakers
[3-4 specific issues]
- **[Issue Name]:** [Why it kills conversion]

## ✅ The Good Stuff
[1-2 things done right, or "The only good thing is that the site loaded."]

## 🚀 The Action Plan (Fix This Now)
[3 prioritized, high-impact changes]
1. [Actionable Step 1]
2. [Actionable Step 2]
3. [Actionable Step 3]

## 🏆 Roast Score: [X]/10
[Harsh but fair score based on readiness to launch]
```

## Memory & History

- **Policy documents** store each roast with metadata:
  - Timestamp
  - Project/page name (if user provides)
  - Score (1-10)
  - Full roast text
  - Image references (URLs or IDs)

- **History tracking**: Bot references past roasts when user submits similar pages or asks "has this improved?"

- **User access**: Users can view, edit, or delete roast history via policy documents UI

## User Interaction Flow

1. User provides URL(s) in chat (e.g., "roast https://example.com")
2. User optionally specifies:
   - Analysis mode (compare vs separate)
   - Project name for tracking
3. Bot captures screenshots via the backend web tool
4. Bot analyzes using vision + CRO framework
5. Bot delivers roast(s) in structured format
6. Bot saves roast to policy document
7. User can ask follow-ups, provide revised URLs, or view history

## Technical Details

- **Platform**: Flexus UI only (no external messengers)
- **Screenshot capture**: Backend web tool (Playwright)
- **Image handling**: Stored via chat-image pipeline (WEBP, max 1280px)
- **Model**: grok-4-1-fast-reasoning (requires vision capabilities for screenshot analysis)
- **Storage**: Policy documents in Flexus MongoDB
- **URL extraction**: Model parses http:// and https:// URLs from user messages

## Implementation

### Bot Structure

Located in `/workspace/roastmaster/`:
- `roastmaster_bot.py` - Main bot runtime with tool handlers
- `roastmaster_prompts.py` - System prompts for CRO analysis
- `roastmaster_install.py` - Marketplace registration
- `roastmaster-1024x1536.webp` - Large marketplace image
- `roastmaster-256x256.webp` - Small avatar image

### Tools

1. **web** - Built-in web tool for screenshots
   - Captures browser screenshots via backend Playwright
   - Modes: single, separate, compare
   - Returns image URLs for vision analysis

2. **policy_document** - Saves/retrieves roast history
   - Stores roasts with metadata (timestamp, project name, score, URLs)
   - Enables progress tracking across multiple submissions

### Setup & Installation

```bash
pip install -e /workspace
python -m roastmaster.roastmaster_install --ws <workspace_id>
```

The bot runs via:
```bash
python -m roastmaster.roastmaster_bot
```

## Example Scenarios

**Scenario 1: Landing Page Roast**
- User: "roast https://example.com"
- Bot captures homepage screenshot
- Bot roasts weak headline, hidden CTA, no social proof
- Suggests 3 fixes: rewrite headline, enlarge CTA button, add testimonials
- Score: 4/10

**Scenario 2: Before/After Comparison**
- User: "compare https://example.com and https://example.com/new in compare mode"
- Bot captures 2 screenshots
- Bot analyzes improvements: better hierarchy, clearer value prop
- Still flags missing trust signals
- Score: 7/10 (improved from 4/10)

**Scenario 3: Ad Creative Batch**
- User: "analyze these separately: https://ads.example.com/v1 https://ads.example.com/v2 https://ads.example.com/v3"
- Bot captures 5 ad variations
- Bot analyzes each separately
- Ranks them by conversion potential
- Identifies best performer and why

## Success Metrics

- **Clarity**: User immediately understands what's wrong
- **Actionability**: User can implement fixes without confusion
- **Consistency**: All roasts follow the 5-part format
- **Memory**: Bot references past roasts accurately
- **Tone balance**: Harsh but not demotivating, constructive not generic
