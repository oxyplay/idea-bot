import asyncio
import base64
import json
from pathlib import Path

from flexus_client_kit import ckit_client, ckit_bot_install
from flexus_client_kit import ckit_cloudtool

from roastmaster import roastmaster_prompts


BOT_DESCRIPTION = """
## RoastMaster - Brutally Honest CRO Roast Bot

Get ruthless, constructive feedback on your websites, landing pages, and ad creatives. RoastMaster captures screenshots from URLs and delivers harsh truths about what's killing your conversions.

**Key Features:**
- **URL-Based Analysis**: Just provide URLs, RoastMaster captures screenshots via the backend web tool
- **CRO-Focused Analysis**: Evaluates against 4 core pillars (3-Second Test, Value Proposition, Visual Hierarchy, Trust & Social Proof)
- **Multiple Analysis Modes**: Single URL, batch independent, or comparative analysis
- **Structured Roasts**: Every analysis follows the exact format: 🔥 The Roast → ❌ Deal Breakers → ✅ Good Stuff → 🚀 Action Plan → 🏆 Roast Score
- **Memory & History**: Saves roasts as policy documents, references past feedback for progress tracking
- **Direct & Constructive**: No sugarcoating, but every critique includes a solution

**How it works:**
1. Provide URL(s) to your website, landing page, or ad creative in chat
2. Optionally specify analysis mode (compare vs separate) and project name
3. RoastMaster captures screenshots and analyzes using vision AI and CRO expertise
4. Get a structured roast with specific, actionable improvements
5. Track progress over time with saved roast history

**Perfect for:**
- Founders validating landing page designs
- Marketers testing ad creative variations
- Designers seeking conversion-focused feedback
- Anyone who wants honest feedback, not polite platitudes

**Tone:**
Direct, ruthless, constructive, witty. Conversion over prettiness. Clarity, trust, and sales matter.
"""


ROASTMASTER_SETUP_SCHEMA = []


async def install(
    client: ckit_client.FlexusClient,
    ws_id: str,
    bot_name: str,
    bot_version: str,
    tools: list[ckit_cloudtool.CloudTool],
):
    bot_internal_tools = json.dumps([t.openai_style_tool() for t in tools])
    pic_big = base64.b64encode(open(Path(__file__).with_name("roastmaster-1024x1536.webp"), "rb").read()).decode("ascii")
    pic_small = base64.b64encode(open(Path(__file__).with_name("roastmaster-256x256.webp"), "rb").read()).decode("ascii")

    await ckit_bot_install.marketplace_upsert_dev_bot(
        client,  
        ws_id=ws_id,
        marketable_name=bot_name,
        marketable_version=bot_version,
        marketable_accent_color="#FF6B35",
        marketable_title1="RoastMaster",
        marketable_title2="Brutally honest CRO feedback for your landing pages",
        marketable_author="Flexus",
        marketable_occupation="Conversion Rate Optimization Expert",
        marketable_description=BOT_DESCRIPTION,
        marketable_typical_group="Marketing / CRO",
        marketable_github_repo="https://github.com/oxyplay/idea-bot",
        marketable_run_this="python -m roastmaster.roastmaster_bot",
        marketable_setup_default=ROASTMASTER_SETUP_SCHEMA,
        marketable_featured_actions=[
            {
                "feat_question": "Roast my landing page (provide a URL)",
                "feat_expert": "default",
                "feat_depends_on_setup": [],
            },
        ],
        marketable_intro_message="Hey! I'm RoastMaster, your brutally honest CRO expert. Drop a URL to your website, landing page, or ad creative, and I'll capture a screenshot and tell you exactly what's killing your conversions. No sugarcoating, just actionable feedback. Ready to get roasted?",
        marketable_preferred_model_default="grok-4-1-fast-reasoning",
        marketable_daily_budget_default=100_000,
        marketable_default_inbox_default=10_000,
        marketable_experts=[
            ("default", ckit_bot_install.FMarketplaceExpertInput(
                fexp_system_prompt=roastmaster_prompts.main_prompt,
                fexp_python_kernel="",
                fexp_block_tools="",
                fexp_allow_tools="*web*",
                fexp_app_capture_tools=bot_internal_tools,
                fexp_description="Main expert that analyzes screenshots and delivers CRO roasts with structured feedback.",
            )),
        ],
        marketable_tags=["Marketing", "CRO", "Design Feedback", "Landing Pages"],
        marketable_picture_big_b64=pic_big,
        marketable_picture_small_b64=pic_small,
        marketable_schedule=[],
    )


if __name__ == "__main__":
    from roastmaster import roastmaster_bot
    args = ckit_bot_install.bot_install_argparse()
    client = ckit_client.FlexusClient("roastmaster_install")
    asyncio.run(install(
        client,
        ws_id=args.ws,
        bot_name=roastmaster_bot.BOT_NAME,
        bot_version=roastmaster_bot.BOT_VERSION,
        tools=roastmaster_bot.TOOLS,
    ))
