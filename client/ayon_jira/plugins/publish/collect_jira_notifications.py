# -*- coding: utf-8 -*-
"""Collect metadata for Jira integration from Settings."""
import pyblish.api

from ayon_core.lib.profiles_filtering import filter_profiles
from ayon_core.lib import attribute_definitions
from ayon_core.pipeline import AYONPyblishPluginMixin


class CollectJiraNotifications(pyblish.api.InstancePlugin,
                               AYONPyblishPluginMixin):
    """Collects login credentials for Jira"""
    order = pyblish.api.CollectorOrder
    label = "Collect Jira Notifications"
    settings_category = "jira"

    profiles = []

    @classmethod
    def get_attribute_defs(cls):
        return [
            attribute_definitions.TextDef(
                # Key under which it will be stored
                "additional_message",
                # Use plugin label as label for attribute
                label="Additional Jira message",
                placeholder="<Only if Jira is configured>"
            )
        ]

    def process(self, instance):
        profile = self._find_profile(instance)

        if not profile:
            self.log.info("No profile found, notification won't be send")
            return

        self.log.info("Found profile: {}".format(profile))
        instance.data.setdefault("families", []).append("jira")

        jira_message_meta = {
            "jira_message": profile["comment"]
        }
        attribute_values = self.get_attr_values_from_data(instance.data)
        additional_message = attribute_values.get("additional_message")
        if additional_message:
            jira_message_meta["jira_additional_message"] = additional_message

        instance.data.setdefault("jira", {}).update(jira_message_meta)

    def _find_profile(self, instance):
        task_entity = instance.data.get("taskEntity")
        task_name = task_type = None
        if task_entity:
            task_name = task_entity["name"]
            task_type = task_entity["taskType"]
        product_type = instance.data["productType"]
        key_values = {
            "product_types": product_type,
            "task_names": task_name,
            "task_types": task_type,
            "hosts": instance.context.data["hostName"],
            "product_names": instance.data["productName"],
        }
        # Filter 'key_values' for backwards compatibility
        if self.profiles:
            profile_keys = set(self.profiles[0].keys())
            key_values = {
                key: value
                for key, value in key_values.items()
                if key in profile_keys
            }
        profile = filter_profiles(self.profiles, key_values,
                                  logger=self.log)
        return profile
