import asyncio
import logging
import json
import re
import time
from typing import Dict, Any, List

import requests
from pymongo import AsyncMongoClient

from flexus_client_kit import ckit_client
from flexus_client_kit import ckit_cloudtool
from flexus_client_kit import ckit_bot_exec
from flexus_client_kit import ckit_shutdown
from flexus_client_kit import ckit_ask_model
from flexus_client_kit import ckit_mongo
from idea_bot import reddit_opportunity_scanner_install
from idea_bot import reddit_opportunity_scanner_prompts

logger = logging.getLogger("bot_reddit_opportunity_scanner")

BOT_NAME = "reddit_opportunity_scanner"
BOT_VERSION = "0.1.0"

REDDIT_USER_AGENT = "Mozilla/5.0 (compatible; RedditScanner/1.0)"


SCAN_REDDIT_TOOL = ckit_cloudtool.CloudTool(
    strict=True,
    name="scan_reddit",
    description="Scan specified subreddits for business opportunities by analyzing posts and comments",
    parameters={
        "type": "object",
        "properties": {
            "subreddit_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of subreddit names to scan (e.g., ['wordpress', 'saas', 'copywriting'])",
            },
        },
        "required": ["subreddit_names"],
        "additionalProperties": False,
    },
)

TOOLS = [SCAN_REDDIT_TOOL]


def fetch_reddit_json(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": REDDIT_USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {}


def extract_posts(subreddit: str, limit: int = 50) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    data = fetch_reddit_json(url)

    if not data or "data" not in data or "children" not in data["data"]:
        logger.warning(f"No data found for r/{subreddit}")
        return []

    posts = []
    for child in data["data"]["children"]:
        post_data = child.get("data", {})
        upvotes = post_data.get("ups", 0)
        if upvotes >= 0:
            posts.append({
                "id": post_data.get("id", ""),
                "title": post_data.get("title", ""),
                "selftext": post_data.get("selftext", ""),
                "upvotes": upvotes,
                "num_comments": post_data.get("num_comments", 0),
                "engagement": upvotes + post_data.get("num_comments", 0),
            })

    posts.sort(key=lambda p: p["engagement"], reverse=True)
    return posts[:30]


def extract_comments_recursive(comment_data: Dict[str, Any]) -> List[str]:
    comments = []

    if comment_data.get("kind") == "t1":
        body = comment_data.get("data", {}).get("body", "")
        if body and body not in ["[deleted]", "[removed]"]:
            comments.append(body)

    replies = comment_data.get("data", {}).get("replies", {})
    if isinstance(replies, dict) and "data" in replies:
        for child in replies["data"].get("children", []):
            comments.extend(extract_comments_recursive(child))

    return comments


def fetch_post_comments(subreddit: str, post_id: str) -> List[str]:
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
    data = fetch_reddit_json(url)

    if not data or not isinstance(data, list) or len(data) < 2:
        return []

    comments = []
    comment_listing = data[1]
    if "data" in comment_listing and "children" in comment_listing["data"]:
        for child in comment_listing["data"]["children"]:
            comments.extend(extract_comments_recursive(child))

    return comments


def clean_data_for_llm(posts_with_comments: List[Dict[str, Any]]) -> str:
    cleaned = []
    for post in posts_with_comments:
        entry = f"POST: {post['title']}\n"
        if post.get("selftext"):
            entry += f"BODY: {post['selftext']}\n"
        if post.get("comments"):
            entry += "COMMENTS:\n"
            for comment in post["comments"][:20]:
                entry += f"- {comment}\n"
        cleaned.append(entry)
    return "\n\n---\n\n".join(cleaned)


async def analyze_with_llm(cleaned_text: str, setup: Dict[str, Any]) -> str:
    openai_key = setup.get("OPENAI_API_KEY", "")
    anthropic_key = setup.get("ANTHROPIC_API_KEY", "")

    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": reddit_opportunity_scanner_prompts.PRODUCT_DETECTIVE_PROMPT},
                    {"role": "user", "content": cleaned_text},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"ERROR: OpenAI API call failed: {e}"

    elif anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                system=reddit_opportunity_scanner_prompts.PRODUCT_DETECTIVE_PROMPT,
                messages=[
                    {"role": "user", "content": cleaned_text},
                ],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return f"ERROR: Anthropic API call failed: {e}"

    else:
        return "ERROR: No API key configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in bot setup."


async def scan_subreddits(subreddit_names: List[str], setup: Dict[str, Any]) -> str:
    all_posts = []
    total_comments = 0

    for subreddit in subreddit_names:
        logger.info(f"Fetching posts from r/{subreddit}")
        posts = extract_posts(subreddit)

        if not posts:
            continue

        for post in posts:
            time.sleep(2.5)
            logger.info(f"Fetching comments for post {post['id']}")
            comments = fetch_post_comments(subreddit, post["id"])
            post["comments"] = comments
            total_comments += len(comments)

        all_posts.extend(posts)

    if not all_posts:
        return f"No posts found in the specified subreddits: {', '.join(subreddit_names)}"

    cleaned_text = clean_data_for_llm(all_posts)

    header = f"# Reddit Opportunity Analysis\n\nScanned {len(subreddit_names)} subreddits ({len(all_posts)} posts, {total_comments} comments)\n\n"

    if len(cleaned_text) > 50000:
        cleaned_text = cleaned_text[:50000]

    analysis = await analyze_with_llm(cleaned_text, setup)

    return header + analysis


async def reddit_opportunity_scanner_main_loop(
    fclient: ckit_client.FlexusClient,
    rcx: ckit_bot_exec.RobotContext,
) -> None:
    setup = ckit_bot_exec.official_setup_mixing_procedure(
        reddit_opportunity_scanner_install.REDDIT_SETUP_SCHEMA,
        rcx.persona.persona_setup,
    )

    @rcx.on_updated_message
    async def updated_message_in_db(msg: ckit_ask_model.FThreadMessageOutput):
        pass

    @rcx.on_updated_thread
    async def updated_thread_in_db(th: ckit_ask_model.FThreadOutput):
        pass

    @rcx.on_tool_call(SCAN_REDDIT_TOOL.name)
    async def toolcall_scan_reddit(
        toolcall: ckit_cloudtool.FCloudtoolCall,
        model_produced_args: Dict[str, Any],
    ) -> str:
        subreddit_names = model_produced_args.get("subreddit_names", [])

        if not subreddit_names:
            return "ERROR: No subreddit names provided"

        logger.info(f"Scanning subreddits: {subreddit_names}")
        result = await scan_subreddits(subreddit_names, setup)
        return result

    try:
        while not ckit_shutdown.shutdown_event.is_set():
            await rcx.unpark_collected_events(sleep_if_no_work=10.0)
    finally:
        logger.info(f"{rcx.persona.persona_id} exit")


def main():
    scenario_fn = ckit_bot_exec.parse_bot_args()
    fclient = ckit_client.FlexusClient(
        ckit_client.bot_service_name(BOT_NAME, BOT_VERSION),
        endpoint="/v1/jailed-bot",
    )

    asyncio.run(ckit_bot_exec.run_bots_in_this_group(
        fclient,
        marketable_name=BOT_NAME,
        marketable_version_str=BOT_VERSION,
        bot_main_loop=reddit_opportunity_scanner_main_loop,
        inprocess_tools=TOOLS,
        scenario_fn=scenario_fn,
        install_func=reddit_opportunity_scanner_install.install,
    ))


if __name__ == "__main__":
    main()
