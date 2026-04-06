import asyncio
import json
import logging
import os

from flexus_client_kit import ckit_bot_exec, ckit_client, ckit_integrations_db, ckit_shutdown

from roastmaster import roastmaster_install


logger = logging.getLogger("bot_roastmaster")

BOT_NAME = "roastmaster"
BOT_VERSION = "0.0.113"
ROASTMASTER_INTEGRATIONS = roastmaster_install.ROASTMASTER_INTEGRATIONS
TOOLS = [tool for record in ROASTMASTER_INTEGRATIONS for tool in record.integr_tools]


async def roastmaster_main_loop(fclient: ckit_client.FlexusClient, rcx: ckit_bot_exec.RobotContext) -> None:
    setup = ckit_bot_exec.official_setup_mixing_procedure(roastmaster_install.ROASTMASTER_SETUP_SCHEMA, rcx.persona.persona_setup)
    await ckit_integrations_db.main_loop_integrations_init(ROASTMASTER_INTEGRATIONS, rcx, setup)

    if os.environ.get("ROASTMASTER_DEBUG_TOOLS") == "1":
        @rcx.on_updated_message
        async def _debug_log_message(msg) -> None:
            content_preview = msg.ftm_content
            if not isinstance(content_preview, str):
                try:
                    content_preview = json.dumps(content_preview)
                except TypeError:
                    content_preview = repr(content_preview)
            if len(content_preview) > 400:
                content_preview = content_preview[:400] + "..."

            if msg.ftm_tool_calls:
                logger.info(
                    "%s debug assistant message alt=%s num=%s tool_calls=%s content=%r",
                    rcx.persona.persona_id,
                    msg.ftm_alt,
                    msg.ftm_num,
                    msg.ftm_tool_calls,
                    content_preview,
                )
            elif msg.ftm_role in {"assistant", "tool"}:
                logger.info(
                    "%s debug message role=%s alt=%s num=%s content=%r",
                    rcx.persona.persona_id,
                    msg.ftm_role,
                    msg.ftm_alt,
                    msg.ftm_num,
                    content_preview,
                )

    try:
        while not ckit_shutdown.shutdown_event.is_set():
            await rcx.unpark_collected_events(sleep_if_no_work=10.0)
    finally:
        logger.info("%s exit", rcx.persona.persona_id)


def main() -> None:
    scenario_fn = ckit_bot_exec.parse_bot_args()
    fclient = ckit_client.FlexusClient(ckit_client.bot_service_name(BOT_NAME, BOT_VERSION), endpoint="/v1/jailed-bot")
    asyncio.run(ckit_bot_exec.run_bots_in_this_group(
        fclient,
        marketable_name=BOT_NAME,
        marketable_version_str=BOT_VERSION,
        bot_main_loop=roastmaster_main_loop,
        inprocess_tools=TOOLS,
        scenario_fn=scenario_fn,
        install_func=roastmaster_install.install,
    ))


if __name__ == "__main__":
    main()
