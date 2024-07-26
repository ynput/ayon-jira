from ayon_server.settings import (
    BaseSettingsModel,
    ensure_unique_names,
    SettingsField,
)


class PhaseItemModel(BaseSettingsModel):
    _layout = "expanded"
    label: str = SettingsField(
        "",
        title="Phase name",
    )
    value: str = SettingsField(
        "",
        title="Prefix value",
        description="Used to query from list of Jira ticket ids"
    )


class JiraSettings(BaseSettingsModel):
    """Jira addon settings."""

    enabled: bool = SettingsField(True)
    jira_server: str = SettingsField(
        "",
        title="Jira server url",
    )
    jira_username: str = SettingsField(
        "",
        title="Jira username"
    )
    jira_password: str = SettingsField(
        "",
        title="Jira password"
    )
    jira_project_code: str = SettingsField(
        "",
        title="Jira project code"
    )

    phases: list[PhaseItemModel] = SettingsField(
        default_factory=list,
        title="List of process phases",
        description="Allows mapping single AYON task to multiple Jira tickets"
    )


DEFAULT_VALUES = {
    "enabled": True,
    "jira_server": "",
    "jira_username": "",
    "jira_password": "",
    "jira_project_code": "",
    "phases": []
}
