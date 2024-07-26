from ayon_server.settings import (
    BaseSettingsModel,
    ensure_unique_names,
    SettingsField,
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


DEFAULT_VALUES = {}