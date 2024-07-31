import os
import re
import sys
from nxtools import logging
from typing import Any, Dict, Type
from fastapi import Depends, Body, Query, Response

from ayon_server.addons import BaseServerAddon, AddonLibrary
from ayon_server.entities.user import UserEntity
from ayon_server.api import (
    dep_current_user,
    dep_project_name,
)
from ayon_server.lib.postgres import Postgres
from ayon_server.entities.core import attribute_library

from .settings import JiraSettings, DEFAULT_VALUES
from .addon_settings_access import sort_versions

JIRA_ADDON_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__))
)
TEMPLATES_DIR = os.path.join(JIRA_ADDON_DIR, "templates")
TEMPLATE_SUFFIX = "Jira_Template.json".lower()


class JiraAddon(BaseServerAddon):

    settings_model: Type[JiraSettings] = JiraSettings
    frontend_scopes: dict[str, Any] = {"project": {}}
    addon_type = "server"

    def initialize(self):
        logging.info("JiraAddon INIT")

        # first set ayon-python-api
        sys.path.insert(0, os.path.join(JIRA_ADDON_DIR, "vendor"))

        self.add_endpoint(
            "run_template",
            self.run_template,
            method="POST",
        )
        self.add_endpoint(
            "get_templates",
            self.get_templates,
            method="GET",
        )
        self.add_endpoint(
            "get_placeholders",
            self.get_placeholders,
            method="GET",
        )

    async def setup(self):
        need_restart = await self.create_required_attributes()
        if need_restart:
            self.request_server_restart()
        await self._update_enums()

    async def create_required_attributes(self) -> bool:
        """Make sure there are required 'applications' and 'tools' attributes.
        This only checks for the existence of the attributes, it does not
        populate them with any data. When an attribute is added, server needs
        to be restarted, while adding enum data to the attribute does not
        require a restart.

        Returns:
            bool: 'True' if an attribute was created or updated.
        """

        # keep track of the last attribute position (for adding new attributes)
        jira_current_phase_def = self._get_jira_current_phase_def()

        attribute_name = jira_current_phase_def["name"]
        async with Postgres.acquire() as conn, conn.transaction():
            query = (
                f"SELECT BOOL_OR(name = '{attribute_name}') AS "
                 "has_jira_current_phase FROM attributes;"
            )
            result = (await conn.fetch(query))[0]

            attributes_to_create = {}
            if not result["has_jira_current_phase"]:
                attrib_name = jira_current_phase_def["name"]
                attributes_to_create[attrib_name] = {
                    "scope": jira_current_phase_def["scope"],
                    "data": {
                        "title": jira_current_phase_def["title"],
                        "type": jira_current_phase_def["type"],
                        "enum": [],
                    }
                }

            needs_restart = False
            # when any of the required attributes are not present, add them
            # and return 'True' to indicate that server needs to be restarted
            for name, payload in attributes_to_create.items():
                insert_query = "INSERT INTO attributes (name, scope, data, position) VALUES ($1, $2, $3, (SELECT COALESCE(MAX(position), 0) + 1 FROM attributes)) ON CONFLICT DO NOTHING"
                await conn.execute(
                    insert_query,
                    name,
                    payload["scope"],
                    payload["data"],
                )
                needs_restart = True
        return needs_restart

    def _get_jira_current_phase_def(self):
        return {
            "name": "jiraCurrentPhase",
            "type": "string",
            "title": "Jira Current Phase",
            "scope": ["task"],
            "enum": [],
        }

    async def _update_enums(self):
        """Updates applications and tools enums based on the addon settings.
        This method is called when the addon is started (after we are sure that the
        'applications' and 'tools' attributes exist) and when the addon settings are
        updated (using on_settings_updated method).
        """

        instance = AddonLibrary.getinstance()
        app_defs = instance.data.get(self.name)
        phases_enum = []
        for addon_version in sort_versions(
            app_defs.versions.keys(), reverse=True
        ):
            addon = app_defs.versions[addon_version]
            for variant in ("production", "staging"):
                settings_model = await addon.get_studio_settings(variant)
                studio_settings = settings_model.dict()
                for phase in studio_settings["phases"]:
                    if phase not in phases_enum:
                        phases_enum.append(phase)

        jira_attribute_def = self._get_jira_current_phase_def()
        jira_attribute_name = jira_attribute_def["name"]
        jira_attribute_def["enum"] = list(phases_enum)

        phases_scope = jira_attribute_def["scope"]

        jira_attribute_def.pop("scope")
        jira_attribute_def.pop("name")

        phases_matches = False
        async for row in Postgres.iterate(
            "SELECT name, position, scope, data from public.attributes"
        ):
            if row["name"] == jira_attribute_name:
                # Check if scope is matching ftrack addon requirements
                if (
                    set(row["scope"]) == set(phases_scope)
                    and row["data"].get("enum") == phases_enum
                ):
                    phases_matches = True
        if phases_matches:
            return

        if not phases_matches:
            await Postgres.execute(
                """
                UPDATE attributes SET
                    scope = $1,
                    data = $2
                WHERE 
                    name = $3
                """,
                phases_scope,
                jira_attribute_def,
                jira_attribute_name,
            )

        # Reset attributes cache on server
        await attribute_library.load()

    async def on_settings_changed(self, *args, **kwargs):
        _ = args, kwargs
        await self._update_enums()

    async def get_templates(self):
        """Get list of name of templates

        Currently from `server/templates` folder. Each template should have 2
        parts, `Ayon` and `Jira`.
        """
        templates_dir = os.path.join(JIRA_ADDON_DIR, "templates")
        if not os.path.isdir(TEMPLATES_DIR):
            raise RuntimeError(f"No templates directory at {templates_dir}")

        template_names = set()
        for filename in os.listdir(templates_dir):
            filename = filename.lower()
            if TEMPLATE_SUFFIX in filename:
                filename = filename.replace(TEMPLATE_SUFFIX, "").strip("_")
                template_names.add(filename)

        return template_names

    async def get_placeholders(
        self,
        template_name: str = Query(
            ...,
            description="Name of template",
            example="Tier_1_Outfit",
        )
    ):
        """Parses content of JIRA template for unique string in %"""
        template_file_name = f"{template_name}_{TEMPLATE_SUFFIX}"
        template_file_path = os.path.join(TEMPLATES_DIR, template_file_name)
        if not os.path.exists(template_file_path):
            raise RuntimeError(f"{template_file_path} doesn't exist")

        with open(template_file_path, 'r') as file:
            file_content = file.read()

        pattern = r'%([^%]+)%'
        matches = re.findall(pattern, file_content)
        return set(matches)

    async def run_template(
        self,
        user: UserEntity = Depends(dep_current_user),

        body: Dict[str, Any] = Body(
            ...,
            description="Body with all parameters, expected project_name[str]"
                        "jira_project_code[str], template_name[str], "
                        "placeholder_map[dict[str, str]], "
                        "folder_paths[list[str]]"
            ,
        )
    ) -> Response:
        """Creates tasks and jira tickets based on selected values in form"""
        from .templates import create_tasks_and_tickets

        status = await create_tasks_and_tickets(
            user,
            body["project_name"],
            body["jira_project_code"],
            body["template_name"],
            body["placeholder_map"],
            body["folder_paths"]
        )
        if status.errors:
            errors = "\n".join(status.errors)
            return Response(
                status_code=400,
                content=f"{errors} \n\n {status.traceback}")

        return Response(status_code=204, content=f"{status.info()}")
