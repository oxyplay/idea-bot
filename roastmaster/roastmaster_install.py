import argparse
import asyncio
import os
from pathlib import Path

from flexus_client_kit import ckit_client, ckit_integrations_db, ckit_skills, no_special_code_bot


BOT_VERSION = "0.0.9"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install RoastMaster from its manifest")
    parser.add_argument("--ws", help="Workspace ID to install into")
    return parser.parse_args()


async def install() -> None:
    bot_dir = Path(__file__).resolve().parent
    manifest, setup_schema = no_special_code_bot.load_manifest_and_setup_schema(bot_dir)
    skills = ckit_skills.static_skills_find(bot_dir, manifest.get("shared_skills_allowlist", ""))
    integrations = ckit_integrations_db.static_integrations_load(bot_dir, manifest["integrations"], builtin_skills=skills)
    tools = [tool for record in integrations for tool in record.integr_tools]
    client = ckit_client.FlexusClient("roastmaster_install")
    await no_special_code_bot.install_from_manifest(
        manifest,
        setup_schema,
        bot_dir,
        client,
        manifest["bot_name"],
        BOT_VERSION,
        tools,
    )


if __name__ == "__main__":
    args = _parse_args()
    if args.ws:
        os.environ["FLEXUS_WORKSPACE"] = args.ws
    asyncio.run(install())
