import dataclasses
import json
from typing import Any, Dict, List, Optional, Tuple

import gql

from flexus_client_kit import ckit_bot_install, ckit_client, ckit_integrations_db, gql_utils
from flexus_simple_bots import prompts_common


async def marketplace_upsert_dev_bot_compat(
    client: ckit_client.FlexusClient,
    ws_id: str,
    marketable_name: str,
    marketable_version: str,
    marketable_title1: str,
    marketable_title2: str,
    marketable_author: str,
    marketable_accent_color: str,
    marketable_occupation: str,
    marketable_description: str,
    marketable_typical_group: str,
    marketable_github_repo: str,
    marketable_run_this: str,
    marketable_schedule: List[Dict[str, Any]],
    marketable_setup_default: List[Dict[str, Any]],
    marketable_featured_actions: List[Dict[str, Any]],
    marketable_intro_message: str,
    marketable_preferred_model_expensive: str,
    marketable_preferred_model_cheap: str,
    marketable_picture_big_b64: str,
    marketable_picture_small_b64: str,
    marketable_experts: List[Tuple[str, ckit_bot_install.FMarketplaceExpertInput]],
    marketable_tags: Optional[List[str]] = None,
    marketable_daily_budget_default: int = 1_000_000,
    marketable_default_inbox_default: int = 100_000,
    marketable_max_inprogress: int = 2,
    marketable_forms: Optional[Dict[str, str]] = None,
    marketable_required_policydocs: Optional[List[str]] = None,
    marketable_auth_needed: Optional[List[str]] = None,
    marketable_auth_supported: Optional[List[str]] = None,
    marketable_auth_scopes: Optional[Dict[str, List[str]]] = None,
    add_integrations_into_expert_system_prompt: Optional[List[ckit_integrations_db.IntegrationRecord]] = None,
) -> ckit_bot_install.FBotInstallOutput:
    assert ws_id, "Set FLEXUS_WORKSPACE environment variable to your workspace ID"
    assert not ws_id.startswith("fx-"), "Use a workspace ID, not a group ID"

    experts_input = []
    for expert_name, expert in marketable_experts:
        has_a2a = expert._tool_allowed("flexus_hand_over_task")
        sections = [expert.fexp_system_prompt, "# Flexus Environment", prompts_common.PROMPT_KANBAN]
        if has_a2a:
            sections.append(prompts_common.PROMPT_A2A_COMMUNICATION)

        if add_integrations_into_expert_system_prompt:
            for record in add_integrations_into_expert_system_prompt:
                if record.integr_prompt and any(expert._tool_allowed(tool.name) for tool in record.integr_tools):
                    sections.append(record.integr_prompt)

        sections.append(prompts_common.PROMPT_HERE_GOES_SETUP)
        prompt = "\n\n\n".join(section.strip() for section in sections) + "\n"

        prepared = dataclasses.replace(expert, fexp_system_prompt=prompt)
        expert_dict = dataclasses.asdict(prepared)
        expert_dict["fexp_name"] = f"{marketable_name}_{expert_name}"
        experts_input.append(expert_dict)

    http = await client.use_http()
    async with http as h:
        response = await h.execute(
            gql.gql(
                f"""mutation InstallBot($ws: String!, $name: String!, $ver: String!, $title1: String!, $title2: String!, $author: String!, $accent_color: String!, $occupation: String!, $desc: String!, $typical_group: String!, $repo: String!, $run: String!, $setup: String!, $featured: [FFeaturedActionInput!]!, $intro: String!, $model_expensive: String!, $model_cheap: String!, $daily: Int!, $inbox: Int!, $experts: [FMarketplaceExpertInput!]!, $schedule: String!, $big: String!, $small: String!, $tags: [String!]!, $forms: String, $required_policydocs: [String!]!, $auth_needed: [String!]!, $auth_supported: [String!]!, $auth_scopes: String, $max_inprogress: Int!) {{
                    marketplace_upsert_dev_bot(
                        ws_id: $ws,
                        marketable_name: $name,
                        marketable_version: $ver,
                        marketable_title1: $title1,
                        marketable_title2: $title2,
                        marketable_author: $author,
                        marketable_accent_color: $accent_color,
                        marketable_occupation: $occupation,
                        marketable_description: $desc,
                        marketable_typical_group: $typical_group,
                        marketable_github_repo: $repo,
                        marketable_run_this: $run,
                        marketable_setup_default: $setup,
                        marketable_featured_actions: $featured,
                        marketable_intro_message: $intro,
                        marketable_preferred_model_expensive: $model_expensive,
                        marketable_preferred_model_cheap: $model_cheap,
                        marketable_daily_budget_default: $daily,
                        marketable_default_inbox_default: $inbox,
                        marketable_experts: $experts,
                        marketable_schedule: $schedule,
                        marketable_picture_big_b64: $big,
                        marketable_picture_small_b64: $small,
                        marketable_tags: $tags,
                        marketable_forms: $forms,
                        marketable_required_policydocs: $required_policydocs,
                        marketable_auth_needed: $auth_needed,
                        marketable_auth_supported: $auth_supported,
                        marketable_auth_scopes: $auth_scopes,
                        marketable_max_inprogress: $max_inprogress
                    ) {{
                        {gql_utils.gql_fields(ckit_bot_install.FBotInstallOutput)}
                    }}
                }}"""
            ),
            variable_values={
                "ws": ws_id,
                "name": marketable_name,
                "ver": marketable_version,
                "title1": marketable_title1,
                "title2": marketable_title2,
                "author": marketable_author,
                "accent_color": marketable_accent_color,
                "occupation": marketable_occupation,
                "desc": marketable_description,
                "typical_group": marketable_typical_group,
                "repo": marketable_github_repo,
                "run": marketable_run_this,
                "setup": json.dumps(marketable_setup_default),
                "featured": marketable_featured_actions,
                "intro": marketable_intro_message,
                "model_expensive": marketable_preferred_model_expensive,
                "model_cheap": marketable_preferred_model_cheap,
                "daily": marketable_daily_budget_default,
                "inbox": marketable_default_inbox_default,
                "experts": experts_input,
                "schedule": json.dumps(marketable_schedule),
                "big": marketable_picture_big_b64,
                "small": marketable_picture_small_b64,
                "tags": marketable_tags or [],
                "forms": json.dumps(marketable_forms or {}),
                "required_policydocs": marketable_required_policydocs or [],
                "auth_needed": marketable_auth_needed or [],
                "auth_supported": marketable_auth_supported or [],
                "auth_scopes": json.dumps(marketable_auth_scopes) if marketable_auth_scopes else None,
                "max_inprogress": marketable_max_inprogress,
            },
        )

    return gql_utils.dataclass_from_dict(response["marketplace_upsert_dev_bot"], ckit_bot_install.FBotInstallOutput)
