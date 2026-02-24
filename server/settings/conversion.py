from typing import Any


def _convert_product_base_types_0_2_0(overrides: dict) -> None:
    profiles = overrides.get("publish", {}).get("CollectJiraNotifications", {}).get("profiles")
    if not profiles:
        return

    for profile in profiles:
        for old, new in (
            ("host", "host_name"),
            ("product_types", "product_base_types"),
        ):
            if old in profile and new not in profile:
                profile[new] = profile.pop(old)


def convert_settings_overrides(
    source_version: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    _convert_product_base_types_0_2_0(overrides)
    return overrides
