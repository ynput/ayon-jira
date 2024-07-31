# -*- coding: utf-8 -*-
"""Collect metadata for Jira integration from task metadata.

Requires:
    instance.data["taskEntity]

Provides:
    instance.data["jira"]["jira_ticket_id"]
"""
import pyblish.api


class CollectJiraTicket(pyblish.api.InstancePlugin):
    """Collects id for Jira ticket according to current_stage on the task"""
    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect Jira Ticket"
    families = ["jira"]

    def process(self, instance):
        context_data = instance.context.data
        if (not context_data.get("jira") or
                not context_data["jira"]["enabled"]):
            return

        task_entity = instance.data.get("taskEntity")
        if not task_entity:
            return
        task_data = task_entity.get("data", {})
        if not task_data:
            return

        jira_meta = task_data.get("jira")
        if not jira_meta:
            return

        current_stage = self._get_current_stage(task_entity)
        self.log.info(f"Collected stage '{current_stage}'")

        jira_ticket_key = f"{current_stage}_jira_ticket"

        jira_ticket_id = jira_meta.get(jira_ticket_key)
        instance.data["jira"]["jira_ticket_id"] = jira_ticket_id

        self.log.info(f"Collected ticket id '{jira_ticket_id}'")

    def _get_current_stage(self, task_entity):
        return task_entity["attrib"]["jiraCurrentPhase"]

