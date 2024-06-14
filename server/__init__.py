from nxtools import logging

from ayon_server.addons import BaseServerAddon
from ayon_server.entities.user import UserEntity
from fastapi import Depends, Path, Query, Response
from ayon_server.api import (
    dep_current_user,
    dep_project_name,
)

from .templates import run_endpoint


class JiraAddon(BaseServerAddon):

    frontend_scopes: dict[str, dict[str, str]] = {"settings": {}}

    def initialize(self):
        logging.info("JiraAddon INIT")
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
        project_name: str = Depends(dep_project_name),
        template_name: str = Query(
            ...,
            description="Name of processed template",
            example="Tier_1_Outfit",
        ),
        placeholder_map: dict[str] = Query(
            None,
            description="Dictionary of placeholders and their values",
            example="{'Tier1CharacterNameOutfitName': 'Character1'}",
        ),
        folderPaths: list[str] = Query(
            None,
            description="List of folder paths to apply template on",
            example="['characters/Character1']",
        ),
    ):
        """Return a random folder from the database"""
        run_endpoint(project_name, template_name, placeholder_map, folderPaths)
