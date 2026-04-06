import argparse
import asyncio
import base64
import json
import os
from pathlib import Path

from flexus_client_kit import ckit_bot_install, ckit_client, ckit_cloudtool, ckit_integrations_db, ckit_skills
from flexus_simple_bots import prompts_common

from roastmaster import roastmaster_prompts
from roastmaster import roastmaster_marketplace


ROASTMASTER_ROOTDIR = Path(__file__).parent
ROASTMASTER_SKILLS = ckit_skills.static_skills_find(ROASTMASTER_ROOTDIR, shared_skills_allowlist="")
ROASTMASTER_SETUP_SCHEMA = json.loads((ROASTMASTER_ROOTDIR / "setup_schema.json").read_text())
ROASTMASTER_INTEGRATIONS = ckit_integrations_db.static_integrations_load(
    ROASTMASTER_ROOTDIR,
    ["flexus_policy_document"],
    builtin_skills=ROASTMASTER_SKILLS,
)

EXPERTS = [
    ("default", ckit_bot_install.FMarketplaceExpertInput(
        fexp_system_prompt=roastmaster_prompts.SYSTEM_PROMPT,
        fexp_python_kernel="",
        fexp_allow_tools="*web*,flexus_policy_document",
        fexp_description="CRO roast expert for landing pages, websites, and ad creatives.",
        fexp_builtin_skills=ckit_skills.read_name_description(ROASTMASTER_ROOTDIR, ROASTMASTER_SKILLS),
    )),
]

BOT_DESCRIPTION = """# RoastMaster - Landing Page Conversion Roast

Brutally honest CRO feedback for landing pages, websites, and ad creatives.

## What You Get
- Fast first-impression critique based on conversion fundamentals
- Clear deal breakers hurting clarity, trust, and clicks
- Specific fixes ranked by likely impact
- Saved roast history in policy documents for future comparisons

## What RoastMaster Evaluates
- 3-second clarity test
- Value proposition strength
- Visual hierarchy and CTA discoverability
- Trust signals and social proof

## Best For
- Landing page reviews
- Ad creative teardowns
- Before-vs-after comparison roasts
- Conversion-focused design feedback
"""


def _load_pic_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii") if path.exists() else ""


async def install(
    client: ckit_client.FlexusClient,
    bot_name: str,
    bot_version: str,
    tools: list[ckit_cloudtool.CloudTool],
) -> None:
    pic_big = _load_pic_b64(ROASTMASTER_ROOTDIR / "roastmaster-1024x1536.webp")
    pic_small = _load_pic_b64(ROASTMASTER_ROOTDIR / "roastmaster-256x256.webp")

    await roastmaster_marketplace.marketplace_upsert_dev_bot_compat(
        client,
        ws_id=client.ws_id,
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
        marketable_run_this="python -m roastmaster_bot",
        marketable_setup_default=ROASTMASTER_SETUP_SCHEMA,
        marketable_featured_actions=[
            {"feat_question": "Roast my landing page (provide a URL)", "feat_expert": "default", "feat_depends_on_setup": []},
            {"feat_question": "Compare these two landing pages for conversions", "feat_expert": "default", "feat_depends_on_setup": []},
            {"feat_question": "Analyze these ad creatives separately", "feat_expert": "default", "feat_depends_on_setup": []},
        ],
        marketable_intro_message="Hey! I'm RoastMaster, your brutally honest CRO expert. Drop a URL to your website, landing page, or ad creative, and I'll tell you exactly what's killing your conversions. No sugarcoating, just actionable feedback.",
        marketable_preferred_model_default="grok-4-1-fast-reasoning",
        marketable_daily_budget_default=100_000,
        marketable_default_inbox_default=10_000,
        marketable_experts=[(name, expert.filter_tools(tools)) for name, expert in EXPERTS],
        add_integrations_into_expert_system_prompt=ROASTMASTER_INTEGRATIONS,
        marketable_tags=["Marketing", "CRO", "Design Feedback", "Landing Pages"],
        marketable_schedule=[prompts_common.SCHED_PICK_ONE_5M | {"sched_when": "EVERY:1m"}],
        marketable_picture_big_b64=pic_big,
        marketable_picture_small_b64=pic_small,
        marketable_forms={},
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install RoastMaster into a Flexus workspace")
    parser.add_argument("--ws", help="Workspace ID to install into (or set FLEXUS_WORKSPACE)")
    return parser.parse_args()


def _resolve_workspace_id(args: argparse.Namespace) -> str | None:
    return args.ws or os.environ.get("FLEXUS_WORKSPACE")


if __name__ == "__main__":
    args = _parse_args()
    workspace_id = _resolve_workspace_id(args)
    if workspace_id:
        os.environ["FLEXUS_WORKSPACE"] = workspace_id
    else:
        raise SystemExit("Set FLEXUS_WORKSPACE or pass --ws <workspace-id> before running the installer")

    from roastmaster import roastmaster_bot

    client = ckit_client.FlexusClient("roastmaster_install")
    asyncio.run(install(client, bot_name=roastmaster_bot.BOT_NAME, bot_version=roastmaster_bot.BOT_VERSION, tools=roastmaster_bot.TOOLS))
