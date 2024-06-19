import os
import json
import re

# would be be better to use variable from addon, but that way you cannot use
# this script directly for development as addon init depends on Server code
CURRENT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__))
)
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")

CUSTOM_ID_FIELD = "customfield_10035"
AYON_TASK_FIELD = "customfield_10033"
COMPONENT_FIELD = "customfield_10034"


import ayon_api
from ayon_api.operations import OperationsSession


def run_endpoint(
        project_name,
        jira_project_code,
        template_name,
        placeholder_map,
        folder_paths
):
    ayon_template_data = _get_ayon_template_data(
        template_name, placeholder_map)
    jira_template_data = _get_jira_template_data(
        template_name, placeholder_map)

    custom_id_to_jira_id = _process_jira_template_data(
        jira_project_code, jira_template_data)

    _process_ayon_template_data(
        project_name, ayon_template_data, folder_paths, custom_id_to_jira_id)

def _process_ayon_template_data(
        project_name, ayon_template_data, folder_paths, custom_id_to_jira_id):
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
            task_data = _replace_custom_ids(custom_id_to_jira_id, task_data)
            task_type = _convert_task(task_name)
            op_session.create_task(
                project_name,
                task_name,
                task_type,
                folder_entity["id"],
                data=task_data
            )

    op_session.commit()


def _replace_custom_ids(custom_id_to_jira_id, task_data):
    """Replaces custom id from template with real Jira id."""
    for key, value in task_data.items():
        if key == "current_phase":
            continue
        if not value:
            continue
        jira_id = custom_id_to_jira_id.get(value)
        if jira_id:
            task_data[key] = jira_id

    return task_data


def _process_jira_template_data(project_code, jira_template_data):
    print("Starting ")
    from atlassian import Jira

    creds = _get_jira_creds()
    jira_conn = Jira(
        url=creds["url"],
        username=creds["username"],
        password=creds["password"]
    )

    # issues = _get_all_issues(jira_conn, project_code)  # for development
    epics = _get_all_epics(jira_conn, project_code)
    epic_name_to_ids = {
        epic_info["summary"]: epic_id
        for epic_id, epic_info in epics.items()
    }
    custom_id_to_task_id = {}
    for item in jira_template_data["jira_template"]:
        epic_name = item["Epic Link"]
        epic_id = epic_name_to_ids.get(epic_name)
        if not epic_id:
            epic_id = _create_epic(jira_conn, project_code, item)
            epic_name_to_ids[epic_name] = epic_id

        task_id = _create_task(jira_conn, project_code, item, epic_id)
        custom_id = item["Custom ID"]
        custom_id_to_task_id[custom_id] = task_id

    _add_links(custom_id_to_task_id, jira_conn, jira_template_data)

    return custom_id_to_task_id


def _create_task(jira_conn, project_code, item, epic_id):
    custom_id = item["Custom ID"]
    task_dict = {
        "project": {"key": project_code},
        "summary": item["Summary"],
        "issuetype": {"name": "Task"},
        # "component": {"name": "Component"},
        "description": item["Description"],
        # "priority": {"name": item["Priority"]},
        COMPONENT_FIELD: item["Component"],
        CUSTOM_ID_FIELD: f"Character1_{custom_id}",
        # "Original Estimate": {"name": "Priority"},
        # "Int vs Ext": {"name": "Priority"},
    }
    if epic_id:
        task_dict["parent"] = {"id": epic_id}
    task = jira_conn.create_issue(task_dict)
    task_id = task["id"]
    return task_id


def _create_epic(jira_conn, project_code, item):
    epic_dict = {
        "project": {"key": project_code},
        "summary": item["Epic Link"],
        "issuetype": {"name": "Epic"},
    }
    epic = jira_conn.create_issue(epic_dict)
    return  epic["id"]


def _add_links(custom_id_to_task_id, jira_conn, jira_template_data):
    for item in jira_template_data["jira_template"]:
        task_id = custom_id_to_task_id[item["Custom ID"]]
        depends_on_id = item["Depends_On"]

        if depends_on_id:
            depends_on_ids = depends_on_id.split(",")
            for depends_on_id in depends_on_ids:
                depends_on_id = depends_on_id.strip()
                if not depends_on_id:
                    continue
                depends_on_id = custom_id_to_task_id[depends_on_id]
                link_dict = {
                    "type": {"name": "Depends"},
                    "inwardIssue": {"id": task_id},
                    "outwardIssue": {"id": depends_on_id},
                }
                jira_conn.create_issue_link(link_dict)

        blocks_id = item["Unblocks"]

        if blocks_id:
            blocks_ids = blocks_id.split(",")
            for blocks_id in blocks_ids:
                blocks_id = blocks_id.strip()
                if not blocks_id:
                    continue
                blocks_id = custom_id_to_task_id[blocks_id]
                link_dict = {
                    "type": {"name": "Blocks"},
                    "inwardIssue": {"id": task_id},
                    "outwardIssue": {"id": blocks_id},
                }
                jira_conn.create_issue_link(link_dict)


def _get_all_epics(jira_conn, project_code):
    jql_request = (f"project = '{project_code}' AND "
                    "issuetype = Epic ")

    content = jira_conn.jql(jql_request)
    epics = {}
    for epic in content["issues"]:
        epics[epic["id"]] = {
            "key": epic["key"],
            "summary": epic["fields"]["summary"]
        }
    return epics


def _get_all_issues(jira_conn, project_code):
    """Query Jira for all issues in project with `project_code`"""
    jql_request = (f"project = '{project_code}' AND "
                    "issuetype = Task ")
    content = jira_conn.jql(jql_request)
    issues = {}
    for issue in content["issues"]:
        issues[issue["id"]] = {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "custom_id": issue["fields"][CUSTOM_ID_FIELD],
            "ayon_task": issue["fields"][AYON_TASK_FIELD],
        }

    return issues


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


def _set_env_vars(env_path=None):
    if not env_path:
        env_path = os.path.join(CURRENT_DIR, ".env")
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
        value = line[sign_idx+1:]

        os.environ[key] = value


def _get_jira_creds(cred_path=None):
    """Parses .cred file with Jira url, username and password"""
    if not cred_path:
        cred_path = os.path.join(CURRENT_DIR, ".creds")
    if not os.path.exists(cred_path):
        raise RuntimeError(f"{cred_path} does not exist")

    with open(cred_path, "r") as file:
        lines = file.readlines()

    creds = {}
    for line in lines:
        # jira key can contain '=' to split it in just 2
        line = line.strip()
        sign_idx = line.find("=")
        key = line[:sign_idx]
        value = line[sign_idx + 1:]
        creds[key] = value

    return creds


if __name__ == "__main__":
    _set_env_vars()

    placeholder_map = {"Tier1CharacterNameOutfitName": "Character1",
                       "Tier1CharacterName": "Character1"}  # possible not importatn
    project_name = "temp_project_sftp"
    run_endpoint(
        project_name,
        "KAN",
        "Tier_1_Outfit",
        placeholder_map,
        ["Characters/Character1"]
    )
