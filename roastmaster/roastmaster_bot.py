from pathlib import Path

import asyncio

from flexus_client_kit import ckit_client, ckit_bot_exec, ckit_integrations_db, ckit_skills, no_special_code_bot


BOT_NAME = "roastmaster"
BOT_VERSION = "0.0.8"


async def _bot_main_loop(manifest, setup_schema, bot_dir, fclient, rcx) -> None:
    await no_special_code_bot.bot_main_loop(manifest, setup_schema, bot_dir, fclient, rcx)


def main() -> None:
    bot_dir = Path(__file__).resolve().parent
    manifest, setup_schema = no_special_code_bot.load_manifest_and_setup_schema(bot_dir)
    bot_name = manifest["bot_name"]
    skills = ckit_skills.static_skills_find(bot_dir, manifest.get("shared_skills_allowlist", ""))
    integrations = ckit_integrations_db.static_integrations_load(bot_dir, manifest["integrations"], builtin_skills=skills)
    all_tools = [tool for record in integrations for tool in record.integr_tools]
    scenario_fn = ckit_bot_exec.parse_bot_args()
    fclient = ckit_client.FlexusClient(ckit_client.bot_service_name(bot_name, BOT_VERSION), endpoint="/v1/jailed-bot")
    asyncio.run(ckit_bot_exec.run_bots_in_this_group(
        fclient,
        marketable_name=bot_name,
        marketable_version_str=BOT_VERSION,
        bot_main_loop=lambda fc, rcx: _bot_main_loop(manifest, setup_schema, bot_dir, fc, rcx),
        inprocess_tools=all_tools,
        scenario_fn=scenario_fn,
        install_func=lambda client, bn, bv, tools: no_special_code_bot.install_from_manifest(manifest, setup_schema, bot_dir, client, bn, bv, tools),
    ))


if __name__ == "__main__":
    main()
