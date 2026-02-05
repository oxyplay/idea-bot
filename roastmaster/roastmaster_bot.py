import asyncio
import logging
import json
import time
import re
import base64
import io
from typing import Dict, Any, Optional, List

from pymongo import AsyncMongoClient
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from PIL import Image

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
BOT_VERSION = "0.1.2"


ANALYZE_URL_TOOL = ckit_cloudtool.CloudTool(
    strict=True,
    name="analyze_url",
    description="Capture screenshots of website URLs and analyze them for CRO (Conversion Rate Optimization) feedback",
    parameters={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs to capture and analyze (extracted from user message)",
            },
            "mode": {
                "type": "string",
                "enum": ["single", "separate", "compare"],
                "description": "Analysis mode: single (one URL), separate (multiple URLs analyzed independently), compare (multiple URLs analyzed together)",
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
        "required": ["urls", "mode", "project_name", "context"],
        "additionalProperties": False,
    },
)

TOOLS = [
    ANALYZE_URL_TOOL,
    fi_pdoc.POLICY_DOCUMENT_TOOL,
]


def extract_urls_from_text(text: str) -> List[str]:
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    return urls


async def capture_screenshot(url: str) -> Optional[str]:
    browser = None
    try:
        async with async_playwright() as p:
            logger.info(f"Launching browser for {url}")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            screenshot_bytes = await page.screenshot(full_page=True, type="png")

            img = Image.open(io.BytesIO(screenshot_bytes))
            max_height = 8000
            if img.height > max_height:
                ratio = max_height / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                img.save(output, format="PNG")
                screenshot_bytes = output.getvalue()

            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            logger.info(f"Captured screenshot for {url}, size: {len(screenshot_b64)} bytes")
            return screenshot_b64
    except PlaywrightTimeoutError:
        logger.error(f"Timeout while loading {url}")
        return None
    except Exception as e:
        logger.error(f"Error capturing screenshot for {url}: {e}")
        return None
    finally:
        if browser:
            try:
                await browser.close()
                logger.info(f"Browser closed for {url}")
            except Exception as e:
                logger.warning(f"Error closing browser for {url}: {e}")


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

    @rcx.on_tool_call(ANALYZE_URL_TOOL.name)
    async def toolcall_analyze_url(toolcall: ckit_cloudtool.FCloudtoolCall, model_produced_args: Dict[str, Any]) -> str:
        urls = model_produced_args.get("urls", [])
        mode = model_produced_args.get("mode", "single")
        project_name = model_produced_args.get("project_name")
        context = model_produced_args.get("context")

        if not urls:
            return "ERROR: No URLs provided. Please provide at least one URL to analyze."

        logger.info(f"Capturing screenshots for {len(urls)} URL(s), mode={mode}, project={project_name}")

        screenshots = []
        failed_urls = []

        for url in urls:
            screenshot_b64 = await capture_screenshot(url)
            if screenshot_b64:
                screenshots.append({
                    "url": url,
                    "image_b64": screenshot_b64,
                })
            else:
                failed_urls.append(url)

        if not screenshots:
            return f"ERROR: Failed to capture screenshots for all URLs. Failed URLs: {', '.join(failed_urls)}"

        result_parts = []
        if failed_urls:
            result_parts.append(f"WARNING: Failed to capture {len(failed_urls)} URL(s): {', '.join(failed_urls)}")

        result_parts.append(f"Successfully captured {len(screenshots)} screenshot(s). Analysis mode: {mode}.")

        thread = await ckit_ask_model.thread_get(fclient, toolcall.fcall_ft_id)
        if not thread:
            return "ERROR: Could not retrieve thread information"

        for idx, screenshot_data in enumerate(screenshots):
            img_bytes = base64.b64decode(screenshot_data["image_b64"])
            attachment_result = await ckit_ask_model.thread_add_user_message(
                fclient,
                toolcall.fcall_ft_id,
                msg_text=f"Screenshot of {screenshot_data['url']}",
                msg_attachments=[{
                    "att_filename": f"screenshot_{idx}.png",
                    "att_mime": "image/png",
                    "att_data_b64": screenshot_data["image_b64"],
                }],
            )
            logger.info(f"Added screenshot attachment for {screenshot_data['url']}")

        analysis_instructions = []
        if mode == "compare":
            analysis_instructions.append(f"Analyzing {len(screenshots)} URLs together in COMPARISON mode. Compare and contrast them, noting improvements or regressions between versions.")
        elif mode == "separate":
            analysis_instructions.append(f"Analyzing {len(screenshots)} URLs in SEPARATE mode. Provide an independent roast for each URL.")
        else:
            analysis_instructions.append("Analyzing a single URL. Provide one comprehensive roast.")

        if context:
            analysis_instructions.append(f"User context: {context}")

        result_parts.extend(analysis_instructions)
        result_parts.append("\nNow analyzing the screenshot(s) based on the 4 CRO pillars using the vision model...")

        return "\n".join(result_parts)

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
