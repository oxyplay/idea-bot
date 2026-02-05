import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List

from pymongo import AsyncMongoClient

from flexus_client_kit import ckit_client
from flexus_client_kit import ckit_cloudtool
from flexus_client_kit import ckit_bot_exec
from flexus_client_kit import ckit_shutdown
from flexus_client_kit import ckit_ask_model
from flexus_client_kit import ckit_mongo
from flexus_client_kit import ckit_external_auth
from flexus_client_kit.integrations import fi_pdoc
from roastmaster import roastmaster_install
from roastmaster import roastmaster_prompts

logger = logging.getLogger("bot_roastmaster")

BOT_NAME = "roastmaster"
BOT_VERSION = "0.1.0"


ANALYZE_SCREENSHOT_TOOL = ckit_cloudtool.CloudTool(
    strict=True,
    name="analyze_screenshot",
    description="Analyze website/landing page screenshots for CRO (Conversion Rate Optimization) feedback",
    parameters={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["single", "separate", "compare"],
                "description": "Analysis mode: single (one image), separate (multiple images analyzed independently), compare (multiple images analyzed together)",
            },
            "project_name": {
                "type": ["string", "null"],
                "description": "Optional project or page name for tracking",
            },
            "context": {
                "type": ["string", "null"],
                "description": "Optional additional context or specific questions from user",
            },
        },
        "required": ["mode", "project_name", "context"],
        "additionalProperties": False,
    },
)

TOOLS = [
    ANALYZE_SCREENSHOT_TOOL,
    fi_pdoc.POLICY_DOCUMENT_TOOL,
]


async def roastmaster_main_loop(fclient: ckit_client.FlexusClient, rcx: ckit_bot_exec.RobotContext) -> None:
    setup = ckit_bot_exec.official_setup_mixing_procedure(
        roastmaster_install.ROASTMASTER_SETUP_SCHEMA,
        rcx.persona.persona_setup,
    )

    mongo_conn_str = await ckit_mongo.mongo_fetch_creds(fclient, rcx.persona.persona_id)
    mongo = AsyncMongoClient(mongo_conn_str)
    dbname = rcx.persona.persona_id + "_db"
    mydb = mongo[dbname]

    pdoc_integration = fi_pdoc.IntegrationPdoc(rcx, rcx.persona.ws_root_group_id)

    @rcx.on_updated_message
    async def updated_message_in_db(msg: ckit_ask_model.FThreadMessageOutput):
        pass

    @rcx.on_updated_thread
    async def updated_thread_in_db(th: ckit_ask_model.FThreadOutput):
        pass

    @rcx.on_tool_call(ANALYZE_SCREENSHOT_TOOL.name)
    async def toolcall_analyze_screenshot(toolcall: ckit_cloudtool.FCloudtoolCall, model_produced_args: Dict[str, Any]) -> str:
        mode = model_produced_args.get("mode", "single")
        project_name = model_produced_args.get("project_name")
        context = model_produced_args.get("context")

        thread = await ckit_ask_model.thread_get(fclient, toolcall.fcall_ft_id)
        if not thread:
            return "ERROR: Could not retrieve thread information"

        messages = await ckit_ask_model.thread_list_messages(fclient, toolcall.fcall_ft_id)
        if not messages:
            return "ERROR: No messages found in thread"

        images = []
        for msg in reversed(messages):
            if msg.msg_role == "user" and msg.msg_attachments:
                for att in msg.msg_attachments:
                    if att.att_mime and att.att_mime.startswith("image/"):
                        images.append({
                            "att_id": att.att_id,
                            "filename": att.att_filename,
                            "mime": att.att_mime,
                        })

        if not images:
            return "ERROR: No images found in recent messages. Please upload a screenshot first."

        logger.info(f"Found {len(images)} image(s) in thread, mode={mode}, project={project_name}")

        analysis_prompt = roastmaster_prompts.CRO_ANALYSIS_SYSTEM_PROMPT

        if mode == "compare":
            analysis_prompt += f"\n\nYou are analyzing {len(images)} images together in COMPARISON mode. Compare and contrast them, noting improvements or regressions between versions."
        elif mode == "separate":
            analysis_prompt += f"\n\nYou are analyzing {len(images)} images in SEPARATE mode. Provide an independent roast for each image."
        else:
            analysis_prompt += "\n\nYou are analyzing a single image. Provide one comprehensive roast."

        if context:
            analysis_prompt += f"\n\nUser context: {context}"

        return f"Images detected: {len(images)} image(s). Analysis mode: {mode}. The vision model will now analyze the screenshot(s) based on the 4 CRO pillars and return a structured roast in the required format."

    @rcx.on_tool_call(fi_pdoc.POLICY_DOCUMENT_TOOL.name)
    async def toolcall_policy_document(toolcall: ckit_cloudtool.FCloudtoolCall, model_produced_args: Dict[str, Any]) -> str:
        return await pdoc_integration.called_by_model(toolcall, model_produced_args)

    logger.info("RoastMaster bot starting main loop")

    try:
        while not ckit_shutdown.shutdown_event.is_set():
            await rcx.unpark_collected_events(sleep_if_no_work=10.0)
    finally:
        await mongo.close()


def main():
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
