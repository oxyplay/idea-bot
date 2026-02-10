import asyncio
import logging
import json
import time
import re
import base64
import io
import asyncio
from typing import Dict, Any, Optional, List

from pymongo import AsyncMongoClient
from playwright.async_api import ViewportSize, async_playwright, TimeoutError as PlaywrightTimeoutError
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
BOT_VERSION = "1.0.0"


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


async def capture_screenshot(url: str) -> Optional[tuple[str, str]]:
    max_attempts = 3
    nav_timeout = 45_000
    viewport: ViewportSize = {"width": 1920, "height": 1080}
    headers = {"Accept-Language": "en-US,en;q=0.9"}
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    browser = None

    attempt_errors: List[str] = []
    try:
        async with async_playwright() as p:
            logger.info(f"Launching browser for {url}")
            browser = await p.chromium.launch(headless=True)

            for attempt in range(1, max_attempts + 1):
                context = await browser.new_context(viewport=viewport, user_agent=user_agent, extra_http_headers=headers)
                page = await context.new_page()
                try:
                    logger.info(f"Navigating to {url} (attempt {attempt}/{max_attempts})")
                    await page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
                    await page.wait_for_timeout(2000)
                    screenshot_bytes = await page.screenshot(full_page=True, type="png")

                    img = Image.open(io.BytesIO(screenshot_bytes))
                    max_height = 6000
                    if img.height > max_height:
                        ratio = max_height / img.height
                        new_width = int(img.width * ratio)
                        img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                        screenshot_bytes = None
                    max_width = 1600
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                        screenshot_bytes = None

                    if screenshot_bytes is None:
                        optimized = io.BytesIO()
                        img.save(optimized, format="PNG")
                        screenshot_bytes = optimized.getvalue()

                    output = io.BytesIO()
                    img.save(output, format="JPEG", quality=72, optimize=True)
                    jpeg_bytes = output.getvalue()
                    screenshot_bytes = jpeg_bytes

                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                    logger.info(f"Captured screenshot for {url}, size: {len(screenshot_b64)} bytes")
                    return screenshot_b64, "image/jpeg"
                except PlaywrightTimeoutError as exc:
                    message = f"Timeout while loading {url} (attempt {attempt})"
                    logger.warning(message)
                    attempt_errors.append(message + f": {exc}")
                except Exception as exc:
                    message = f"Error capturing screenshot for {url} (attempt {attempt})"
                    logger.error(f"{message}: {exc}")
                    attempt_errors.append(message + f": {exc}")
                finally:
                    await context.close()
                    await asyncio.sleep(1)
    except Exception as exc:
        message = f"Browser failed for {url}"
        logger.error(f"{message}: {exc}")
        attempt_errors.append(message + f": {exc}")
    finally:
        if browser:
            try:
                await browser.close()
                logger.info(f"Browser closed for {url}")
            except Exception as e:
                logger.warning(f"Error closing browser for {url}: {e}")

    if attempt_errors:
        logger.error(f"Failed to capture {url} after {max_attempts} attempts: {' | '.join(attempt_errors)}")
    return None


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
            screenshot = await capture_screenshot(url)
            if screenshot:
                screenshot_b64, mime = screenshot
                screenshots.append({
                    "url": url,
                    "image_b64": screenshot_b64,
                    "mime": mime,
                })
            else:
                failed_urls.append(url)

        if not screenshots:
            return f"ERROR: Failed to capture screenshots for all URLs. Failed URLs: {', '.join(failed_urls)}"

        result_parts = []
        if failed_urls:
            result_parts.append(f"WARNING: Failed to capture {len(failed_urls)} URL(s): {', '.join(failed_urls)}")

        result_parts.append(f"Successfully captured {len(screenshots)} screenshot(s). Analysis mode: {mode}.")

        http = await fclient.use_http()
        try:
            for screenshot_data in screenshots:
                content = [
                    {"m_type": "text", "m_content": f"Screenshot of {screenshot_data['url']}"},
                    {"m_type": screenshot_data.get("mime", "image/png"), "m_content": screenshot_data["image_b64"]},
                ]
                await ckit_ask_model.thread_add_user_message(
                    http,
                    toolcall.fcall_ft_id,
                    content,
                    "roastmaster",
                    ftm_alt=100,
                )
                logger.info(f"Added screenshot attachment for {screenshot_data['url']}")
        finally:
            await http.close_async()

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
