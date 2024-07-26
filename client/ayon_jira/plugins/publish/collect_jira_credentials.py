# -*- coding: utf-8 -*-
"""Collect metadata for Jira integration from Settings."""
import json

import pyblish.api


class CollectJiraCredentials(pyblish.api.ContextPlugin):
    """Collects login credentials for Jira"""
    order = pyblish.api.CollectorOrder
    label = "Collect Jira Credentials"

    def process(self, context):
        project_settings = context.data["project_settings"]
        jira_settings = project_settings["jira"]

        context.data["jira"] = {
            "enabled": jira_settings["enabled"],
            "jira_server": jira_settings["jira_server"],
            "jira_username": jira_settings["jira_username"],
            "jira_password": jira_settings["jira_password"],
            "jira_project_code": jira_settings["jira_project_code"],
        }
