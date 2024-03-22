# Standard imports
import re

# Local imports
from config import (
    PRODUCT_ID,
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    PR_BODY_STARTS_WITH,
    ISSUE_NUMBER_FORMAT,
)

from services.github.github_manager import (
    create_comment_on_issue_with_gitauto_button,
)
from services.github.github_types import (
    GitHubEventPayload,
    GitHubInstallationPayload,
)
from services.supabase import SupabaseManager
from services.gitauto_handler import handle_gitauto

# Initialize managers
supabase_manager = SupabaseManager(url=SUPABASE_URL, key=SUPABASE_SERVICE_ROLE_KEY)


async def handle_installation_created(payload: GitHubInstallationPayload) -> None:
    installation_id: int = payload["installation"]["id"]
    owner_type: str = payload["installation"]["account"]["type"][0]
    owner_name: str = payload["installation"]["account"]["login"]
    owner_id: str = payload["installation"]["account"]["id"]

    supabase_manager.create_installation(
        installation_id=installation_id,
        owner_type=owner_type,
        owner_name=owner_name,
        owner_id=owner_id,
    )


async def handle_installation_deleted(payload: GitHubInstallationPayload) -> None:
    installation_id: int = payload["installation"]["id"]
    supabase_manager.delete_installation(installation_id=installation_id)


async def handle_webhook_event(event_name: str, payload: GitHubEventPayload) -> None:
    """Determine the event type and call the appropriate handler"""
    action: str = payload.get("action")
    if not action:
        return

    # Check the type of webhook event and handle accordingly
    if event_name == "installation" and action in ("created"):
        print("Installation is created")
        await handle_installation_created(payload=payload)

    elif event_name == "installation" and action in ("deleted"):
        print("Installation is deleted")
        await handle_installation_deleted(payload=payload)

    elif event_name == "issues":
        if action == "labeled":
            print("Issue is labeled")
            await handle_gitauto(payload=payload, type="label")
        elif action == "opened":
            create_comment_on_issue_with_gitauto_button(payload=payload)

    # Run agent on proper environment
    elif event_name == "issue_comment" and action == "edited":
        issue_handled = False

        search_text = "- [x] Generate PR"
        if PRODUCT_ID != "gitauto":
            search_text += " - " + PRODUCT_ID
            if payload["comment"]["body"].find(search_text) != -1:
                issue_handled = True
                print("Triggered GitAuto PR")
                await handle_gitauto(payload=payload, type="comment")
        else:
            if (
                payload["comment"]["body"].find(search_text) != -1
                and payload["comment"]["body"].find(search_text + " - ") == -1
            ):
                issue_handled = True
                print("Triggered GitAuto PR")
                await handle_gitauto(payload=payload, type="comment")
        if not issue_handled:
            print("Edit is not an activated GitAtuo trigger.")

    elif event_name == "pull_request" and action == "closed":
        pull_request = payload.get("pull_request")
        if not pull_request:
            return

        # Check PR is merged and this is correct GitAuto environment
        if pull_request["merged_at"] is not None and pull_request["head"][
            "ref"
        ].startswith(PRODUCT_ID + ISSUE_NUMBER_FORMAT):
            # Create unique_issue_id to update merged status
            body = pull_request["body"]
            if not body.startswith(PR_BODY_STARTS_WITH):
                return
            pattern = re.compile(r"/issues/(\d+)")
            match = re.search(pattern, body)
            if not match:
                return
            issue_number = match.group(1)
            owner_type = payload["repository"]["owner"]["type"][0]
            unique_issue_id = f"{owner_type}/{payload['repository']['owner']['login']}/{payload['repository']['name']}#{issue_number}"
            supabase_manager.set_issue_to_merged(unique_issue_id=unique_issue_id)
