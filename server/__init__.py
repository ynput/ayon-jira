import os
import sys
from nxtools import logging

from ayon_server.addons import BaseServerAddon
from ayon_server.entities.user import UserEntity
from fastapi import Depends, Path, Query, Response
from ayon_server.api import (
    dep_current_user,
    dep_project_name,
)

JIRA_ADDON_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__))
)


class JiraAddon(BaseServerAddon):

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

    async def setup(self):
        pass


    async def run_template(
        self,
        user: UserEntity = Depends(dep_current_user),
        project_name: str = Query(
            ...,
            description="Project name",
            example="test_ayon",
        ),
        template_name: str = Query(
            ...,
            description="Name of processed template",
            example="Tier_1_Outfit",
        ),
        # placeholder_map: list[str] = Query(
        #     None,
        #     description="Dictionary of placeholders and their values",
        #     example="{'Tier1CharacterNameOutfitName': 'Character1'}",
        # ),
        folderPaths: list[str] = Query(
            None,
            description="List of folder paths to apply template on",
            example="['characters/Character1']",
        ),
    ):
        """Return a random folder from the database"""
        from .templates import run_endpoint
        placeholder_map = {"Tier1CharacterNameOutfitName": "Character1",
                           "Tier1CharacterName": "Character1"}  # possible not importatn
        run_endpoint(project_name, template_name, placeholder_map, folderPaths)
