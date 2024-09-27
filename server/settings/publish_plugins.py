from ayon_server.settings import (
    BaseSettingsModel,
    task_types_enum,
    SettingsField
)


class Profile(BaseSettingsModel):
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names")
    product_names: list[str] = SettingsField(
        default_factory=list, title="Product names")
    product_types: list[str] = SettingsField(
        default_factory=list, title="Product types")

    _desc = ("Message sent to ticked selected by profile. "
             "Message template can contain {} placeholders from anatomyData ")
    comment: str = SettingsField(
        "",
        title="Comment to ticket",
        description=_desc,
        widget="textarea"
    )
    upload_thumbnail: bool = SettingsField(
        False,
        title="Upload thumbnail"
    )
    upload_review: bool = SettingsField(
        False,
        title="Upload review"
    )
    review_size_limit: int = SettingsField(
        5,
        title="Review file size limit (MB)"
    )


class CollectJiraNotificationsPlugin(BaseSettingsModel):
    _isGroup = True
    enabled: bool = SettingsField(True)
    optional: bool = SettingsField(False, title="Optional")

    profiles: list[Profile] = SettingsField(
        default_factory=list,
        title="Profiles",
    )


class JiraPublishPlugins(BaseSettingsModel):
    CollectJiraNotifications: CollectJiraNotificationsPlugin = SettingsField(
        title="Notification to Jira",
        default_factory=CollectJiraNotificationsPlugin,
    )
