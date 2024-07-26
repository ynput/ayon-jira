import os
import sys
from nxtools import logging
from typing import Any, Dict, Type
from fastapi import Depends, Body

from ayon_server.addons import BaseServerAddon
from ayon_server.entities.user import UserEntity
from ayon_server.api import (
    dep_current_user,
    dep_project_name,
)

from .settings import JiraSettings, DEFAULT_VALUES

JIRA_ADDON_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__))
)


class JiraAddon(BaseServerAddon):

    settings_model: Type[JiraSettings] = JiraSettings
    frontend_scopes: dict[str, dict[str, str]] = {"settings": {}}

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

    async def setup(self):
        pass

    async def get_templates(self):
        templates_dir = os.path.join(JIRA_ADDON_DIR, "templates")
        if not os.path.isdir(templates_dir):
            raise RuntimeError(f"No templates directory at {templates_dir}")

        template_names = set()
        template_suffix = "Ayon_Template.json".lower()
        for filename in os.listdir(templates_dir):
            filename = filename.lower()
            if template_suffix in filename:
                filename = filename.replace(template_suffix, "").strip("_")
                template_names.add(filename)

        return template_names

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
    ):
        """Return a random folder from the database"""
        from .templates import run_endpoint
        logging.info("\n".join(sys.path))
        logging.info(body)

        run_endpoint(
            body["project_name"],
            body["jira_project_code"],
            body["template_name"],
            body["placeholder_map"],
            body["folder_paths"]
        )

    def _set_env_vars(env_path=None):
        if not env_path:
            env_path = os.path.join(JIRA_ADDON_DIR, ".env")
        if not os.path.exists(env_path):
            raise RuntimeError(f"{env_path} does not exist")

        with open(env_path, "r") as file:
            lines = file.readlines()

        for line in lines:
            # Process each line here
            if "=" not in line:
                continue

            # jira key can contain '=' to split it in just 2
            line = line.strip()
            sign_idx = line.find("=")
            key = line[:sign_idx]
            value = line[sign_idx + 1:]

            os.environ[key] = value
