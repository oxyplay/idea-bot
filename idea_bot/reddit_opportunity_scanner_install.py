import asyncio
import base64
import json
from pathlib import Path

from flexus_client_kit import ckit_client, ckit_bot_install
from flexus_client_kit import ckit_cloudtool

from idea_bot import reddit_opportunity_scanner_prompts


BOT_DESCRIPTION = """
## Reddit Opportunity Scanner - Find Business Ideas from Real Problems

Automatically discover business opportunities by analyzing Reddit discussions. This bot scans subreddits to identify pain points, feature gaps, and unmet needs that people are willing to pay to solve.

**Key Features:**
- **Multi-subreddit scanning**: Analyze posts and comments from multiple subreddits simultaneously
- **Smart filtering**: Focuses on high-engagement posts with real pain points
- **LLM-powered analysis**: Uses GPT-4o-mini or Claude Haiku to identify actionable opportunities
- **Structured reports**: Returns markdown tables with pain points, evidence, intensity, and monetization ideas
- **Gold Nugget recommendations**: Highlights the single best opportunity with clear justification

**How it works:**
1. You provide subreddit names (e.g., "Scan wordpress, saas, copywriting")
2. Bot fetches recent posts and top comments
3. AI analyzes the content for recurring complaints, feature requests, and willingness-to-pay signals
4. Returns a structured report with business opportunity recommendations

**Perfect for:**
- Entrepreneurs seeking validated micro-SaaS ideas
- Product builders looking for real market problems
- Indie hackers researching niche opportunities

**Requirements:**
- OpenAI API key (for GPT-4o-mini) OR Anthropic API key (for Claude Haiku)
- No Reddit API authentication needed (uses public JSON endpoints)
"""


REDDIT_SETUP_SCHEMA = [
    {
        "bs_name": "OPENAI_API_KEY",
        "bs_type": "string_long",
        "bs_default": "",
        "bs_group": "LLM Configuration",
        "bs_order": 1,
        "bs_importance": 1,
        "bs_description": "OpenAI API key for GPT-4o-mini analysis (if not using Anthropic)",
    },
    {
        "bs_name": "ANTHROPIC_API_KEY",
        "bs_type": "string_long",
        "bs_default": "",
        "bs_group": "LLM Configuration",
        "bs_order": 2,
        "bs_importance": 1,
        "bs_description": "Anthropic API key for Claude Haiku analysis (if not using OpenAI)",
    },
]


async def install(
    client: ckit_client.FlexusClient,
    ws_id: str,
    bot_name: str,
    bot_version: str,
    tools: list[ckit_cloudtool.CloudTool],
):
    bot_internal_tools = json.dumps([t.openai_style_tool() for t in tools])
    pic_big = base64.b64encode(open(Path(__file__).with_name("reddit_opportunity_scanner-1024x1536.webp"), "rb").read()).decode("ascii")
    pic_small = base64.b64encode(open(Path(__file__).with_name("reddit_opportunity_scanner-256x256.webp"), "rb").read()).decode("ascii")

    await ckit_bot_install.marketplace_upsert_dev_bot(
        client,
        ws_id=ws_id,
        marketable_name=bot_name,
        marketable_version=bot_version,
        marketable_accent_color="#FF4500",
        marketable_title1="Reddit Opportunity Scanner",
        marketable_title2="Discover business opportunities from Reddit discussions",
        marketable_author="Flexus",
        marketable_occupation="Business Intelligence Assistant",
        marketable_description=BOT_DESCRIPTION,
        marketable_typical_group="Research / Market Intelligence",
        marketable_github_repo="https://github.com/yourusername/reddit-opportunity-scanner",
        marketable_run_this="python -m idea_bot.reddit_opportunity_scanner_bot",
        marketable_setup_default=REDDIT_SETUP_SCHEMA,
        marketable_featured_actions=[
            {
                "feat_question": "Scan wordpress, woocommerce, shopify for opportunities",
                "feat_expert": "default",
                "feat_depends_on_setup": ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
            },
        ],
        marketable_intro_message="Hi! I'm the Reddit Opportunity Scanner. Give me a list of subreddit names and I'll analyze posts and comments to identify business opportunities. For example, try: 'Scan wordpress, saas, copywriting'",
        marketable_preferred_model_default="grok-4-1-fast-non-reasoning",
        marketable_daily_budget_default=100_000,
        marketable_default_inbox_default=10_000,
        marketable_experts=[
            ("default", ckit_bot_install.FMarketplaceExpertInput(
                fexp_system_prompt=reddit_opportunity_scanner_prompts.main_prompt,
                fexp_python_kernel="",
                fexp_block_tools="*setup*",
                fexp_allow_tools="",
                fexp_app_capture_tools=bot_internal_tools,
                fexp_description="Main expert that handles Reddit scanning requests and returns opportunity analysis reports.",
            )),
        ],
        marketable_tags=["Research", "Business Intelligence", "Market Analysis", "Reddit"],
        marketable_picture_big_b64=pic_big,
        marketable_picture_small_b64=pic_small,
        marketable_schedule=[],
    )


if __name__ == "__main__":
    from idea_bot import reddit_opportunity_scanner_bot
    args = ckit_bot_install.bot_install_argparse()
    client = ckit_client.FlexusClient("reddit_opportunity_scanner_install")
    asyncio.run(install(
        client,
        ws_id=args.ws,
        bot_name=reddit_opportunity_scanner_bot.BOT_NAME,
        bot_version=reddit_opportunity_scanner_bot.BOT_VERSION,
        tools=reddit_opportunity_scanner_bot.TOOLS,
    ))
