import os
import re
import copy

import pyblish.api

from atlassian import Jira

from ayon_core.lib.plugin_tools import prepare_template_data
from ayon_core.pipeline.publish import get_publish_repre_path


class IntegrateJiraComment(pyblish.api.InstancePlugin):
    """ Send message notification to a channel.

    Triggers on instances with "jira" family, filled by
    'collect_jira_notifications'.
    Expects configured profile in
    `ayon+settings://jira/publish/CollectJiraNotifications`

    Message template can contain {} placeholders from anatomyData.
    """
    order = pyblish.api.IntegratorOrder + 0.499
    label = "Integrate Jira Comment"
    families = ["jira"]
    settings_category = "jira"

    optional = True

    def process(self, instance):
        jira_metadata = instance.data.get("jira")
        if not jira_metadata:
            self.log.warning("No jira metadata collected, skipping")
            return

        jira_ticket_key = jira_metadata.get("jira_ticket_id")
        if not jira_ticket_key:
            self.log.info("Not collected jira ticket key, skipping")
            return

        thumbnail_path = self._get_thumbnail_path(instance)
        review_path = self._get_review_path(instance)

        message = ""

        additional_message = jira_metadata.get("jira_additional_message")
        if additional_message:
            message = f"{additional_message} \n"

        message += self._get_filled_message(
            jira_metadata["jira_message"], instance)
        if not message:
            self.log.warning("Unable to fill message, skipping")
            return

        jira_credentials = instance.context.data["jira"]

        jira_conn = Jira(
            url=jira_credentials["jira_server"],
            username=jira_credentials["jira_username"],
            password=jira_credentials["jira_password"]
        )

        if jira_metadata["upload_thumbnail"] and thumbnail_path:
            jira_conn.add_attachment(jira_ticket_key,
                                     thumbnail_path)

        if jira_metadata["upload_review"] and review_path:
            message = self._handle_review_upload(
                jira_conn,
                jira_ticket_key,
                message,
                jira_metadata["review_size_limit"],
                review_path
            )

        jira_conn.issue_add_comment(jira_ticket_key, message)

    def _handle_review_upload(
            self,
            jira_conn,
            jira_key,
            message,
            review_upload_limit,
            review_path
    ):
        """Check if uploaded file is not too large"""
        review_file_size_MB = os.path.getsize(review_path) / 1024 / 1024
        if review_file_size_MB > review_upload_limit:
            message += "\nReview upload omitted because of file size."
            if review_path not in message:
                message += "\nFile located at: {}".format(review_path)
        else:
            jira_conn.add_attachment(jira_key, review_path)
        return message

    def _get_filled_message(self, message_templ, instance):
        """Use message_templ and data from instance to get message content.

        Reviews might be large, so allow only adding link to message instead of
        uploading only.
        """

        fill_data = copy.deepcopy(instance.data["anatomyData"])
        # Make sure version is string
        # TODO remove when fixed in ayon-core 'prepare_template_data' function
        fill_data["version"] = str(fill_data["version"])

        multiple_case_variants = prepare_template_data(fill_data)
        fill_data.update(multiple_case_variants)
        message = ""
        try:
            message = self._escape_missing_keys(
                message_templ, fill_data
            ).format(**fill_data)
        except Exception:
            # shouldn't happen
            self.log.warning(
                "Some keys are missing in {}".format(message_templ),
                exc_info=True)

        return message

    def _get_thumbnail_path(self, instance):
        """Returns abs url for thumbnail if present in instance repres"""
        thumbnail_path = None
        for repre in instance.data.get("representations", []):
            if repre.get("thumbnail") or "thumbnail" in repre.get("tags", []):
                repre_thumbnail_path = get_publish_repre_path(
                    instance, repre, False
                )
                if os.path.exists(repre_thumbnail_path):
                    thumbnail_path = repre_thumbnail_path
                break
        return thumbnail_path

    def _get_review_path(self, instance):
        """Returns abs url for review if present in instance repres"""
        review_path = None
        for repre in instance.data.get("representations", []):
            tags = repre.get("tags", [])
            if (
                repre.get("review")
                or "review" in tags
                or "burnin" in tags
            ):
                repre_review_path = get_publish_repre_path(
                    instance, repre, False
                )
                if repre_review_path and os.path.exists(repre_review_path):
                    review_path = repre_review_path
                if "burnin" in tags:  # burnin has precedence if exists
                    break
        return review_path

    def _escape_missing_keys(self, message, fill_data):
        """Double escapes placeholder which are missing in 'fill_data'"""
        placeholder_keys = re.findall(r"\{([^}]+)\}", message)

        fill_keys = []
        for key, value in fill_data.items():
            fill_keys.append(key)
            if isinstance(value, dict):
                for child_key in value.keys():
                    fill_keys.append("{}[{}]".format(key, child_key))

        not_matched = set(placeholder_keys) - set(fill_keys)

        for not_matched_item in not_matched:
            message = message.replace("{}".format(not_matched_item),
                                      "{{{}}}".format(not_matched_item))

        return message
