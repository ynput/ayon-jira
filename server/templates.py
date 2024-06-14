import os
import json
import re

from . import JIRA_ADDON_DIR

TEMPLATES_DIR = os.path.join(JIRA_ADDON_DIR, "templates")


import ayon_api
from ayon_api.operations import OperationsSession

def run_endpoint(project_name, template_name, placeholder_map, folder_paths):
    ayon_template_data = _get_ayon_template_data(
        template_name, placeholder_map)
    jira_template_data = _get_jira_template_data(
        template_name, placeholder_map)

    _process_ayon_template_data(project_name, ayon_template_data, folder_paths)

def _process_ayon_template_data(
        project_name, ayon_template_data, folder_paths):
    tasks = ayon_template_data["ayon_template"]["tasks"]
    if not tasks or not folder_paths:
        return
    op_session = OperationsSession()
    for folder_path in folder_paths:
        folder_entity = ayon_api.get_folder_by_path(project_name, folder_path)
        if not folder_entity:
            print(f"Not found folder for {folder_path}!")
            continue

        for task_name, task_data in tasks.items():
            task_type = _convert_task(task_name)
            op_session.create_task(
                project_name,
                task_name,
                task_type,
                folder_entity["id"],
                data=task_data
            )

    op_session.commit()

def _get_ayon_template_data(template_name, placeholder_map):
    content = _get_template_content(template_name, "Ayon")
    content = _apply_placeholder_map(content, placeholder_map)
    return json.loads(content)

def _get_jira_template_data(template_name, placeholder_map):
    content = _get_template_content(template_name, "Jira")
    content = _apply_placeholder_map(content, placeholder_map)
    return json.loads(content)

def _get_template_content(template_name, side):
    template_name = f"{template_name}_{side}_Template.json"
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        raise RuntimeError(f"{template_path} doesn't exist.")

    data = None
    with open(template_path) as fp:
        data = fp.read()

    return data

def _apply_placeholder_map(template_content, placeholder_map):
    pattern = r"%([^%]+)%"

    matches = re.findall(pattern, template_content)
    for match in matches:
        replace_value = placeholder_map.get(match)
        if not replace_value:
            raise RuntimeError(f"Not found value for {match} "
                               "in {placeholder_map}")
        template_content = template_content.replace(
            f"%{match}%", replace_value)
    return template_content

def _convert_task(task_name):
    """Converts non-existent task types.

    Should be queried from Server.
    """
    convert_tasks = {"Concept": "Generic",
                     "Model": "Modeling"}

    if task_name in convert_tasks:
        return convert_tasks[task_name]
    return task_name


if __name__ == "__main__":

    placeholder_map = {"Tier1CharacterNameOutfitName": "Character1",
                       "Tier1CharacterName": "Character1"}  # possible not importatn
    project_name = "temp_project_sftp"
    run_endpoint(
        project_name,
        "Tier_1_Outfit",
        placeholder_map,
        ["Characters/Character1"]
    )