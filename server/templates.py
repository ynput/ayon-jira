import os
import json
import re

from ayon_server.entities import FolderEntity, TaskEntity
from ayon_server.exceptions import NotFoundException
from ayon_server.lib.postgres import Postgres
from api.tasks.tasks import create_task, update_task

# would be be better to use variable from addon, but that way you cannot use
# this script directly for development as addon init depends on Server code
CURRENT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__))
)
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")

# must be filled with values from Customer !  TODO yank to .ini
CUSTOM_ID_FIELD = "customfield_10035"  # MUST BE ADDED ON Tasks AND Epics
AYON_TASK_FIELD = "customfield_10033"  # MUST BE ADDED ON Tasks
COMPONENT_FIELD = "customfield_10034"  # MUST BE ADDED ON Tasks


async def run_endpoint(
    current_user,
    project_name,
    jira_project_code,
    template_name,
    placeholder_map,
    folder_paths
):
    """Main endpoint - creates Jira and Ayon elements creation."""
    ayon_template_data = _get_ayon_template_data(
        template_name, placeholder_map)
    jira_template_data = _get_jira_template_data(
        template_name, placeholder_map)

    jira_conn = _get_jira_conn()

    folder_paths = _normalize_folder_paths(project_name, folder_paths)

    # create epics and issues in Jira
    custom_id_to_jira_key = _process_jira_template_data(
        jira_conn, jira_project_code, jira_template_data, folder_paths)

    # create ayon tasks, fill Jira keys
    jira_key_to_ayon_task_id = await _process_ayon_template_data(
        current_user,
        project_name,
        ayon_template_data,
        folder_paths,
        custom_id_to_jira_key
    )

    # update Jira issues with AYON tasks
    for jira_key, ayon_task_id in jira_key_to_ayon_task_id.items():
        jira_conn.issue_update(jira_key, {AYON_TASK_FIELD: ayon_task_id})


def _get_jira_conn():
    from atlassian import Jira

    creds = _get_jira_creds()
    jira_conn = Jira(
        url=creds["url"],
        username=creds["username"],
        password=creds["password"]
    )

    return jira_conn


def _normalize_folder_paths(project_name, folder_paths):
    """Remove project_name prefix from folder path.

    Project name could get to folder_by by copy&paste from Server UI, it should
    be removed.
    """
    sanitized_folder_paths = []
    for folder_path in folder_paths:
        if folder_path.startswith(project_name):
            folder_path = folder_path.replace(project_name, "")
        sanitized_folder_paths.append(folder_path)

    return sanitized_folder_paths


async def _process_ayon_template_data(
        current_user,
        project_name,
        ayon_template_data,
        folder_paths,
        custom_id_to_jira_key
):
    """Creates tasks in Ayon for `folder_path` and provides Jira metadata

    Converts Custom IDs from template into real Jira Ids
    """
    print("Starting AYON processing")
    tasks = ayon_template_data["ayon_template"]["tasks"]
    if not tasks or not folder_paths:
        return
    tasks_created = tasks_updated = 0
    for folder_path in folder_paths:
        folder_path = folder_path.strip("/")
        folder_entity = await _get_folder_by_path(project_name, folder_path)

        if not folder_entity:
            print(f"Not found folder for {folder_path}!")
            continue
        existing_tasks = await _get_tasks_for_folder_id(
            project_name, folder_entity.id)

        existing_tasks_by_name = {task.name: task
                                  for task in existing_tasks}

        for task_name, task_data in tasks.items():
            task_data = _replace_custom_ids(custom_id_to_jira_key,
                                            task_data)
            task_type = _convert_task_type(task_name)
            existing_task = existing_tasks_by_name.get(task_name)
            post_data = TaskEntity.model.post_model(
                name=task_name,
                task_type=task_type,
                folderId=folder_entity.id,
                data={"data": {"jira": task_data}}
            )
            if existing_task:
                update_task(
                    post_data,
                    background_tasks=[],
                    user=current_user,
                    project_name=project_name,
                    task_id=existing_task.id,
                )
                tasks_updated += 1
            else:
                create_task(
                    post_data,
                    background_tasks=[],
                    user=current_user,
                    project_name=project_name
                )
                tasks_created += 1

    print("In AYON")
    print(f"Created {tasks_created} issues.")
    print(f"Updated {tasks_updated} issues.")

    jira_key_to_ayon_task_id = await _get_jira_key_to_ayon_task_id(
        custom_id_to_jira_key, folder_entity, project_name, tasks)

    return jira_key_to_ayon_task_id


async def _get_jira_key_to_ayon_task_id(
        custom_id_to_jira_key, folder_entity, project_name, tasks):
    """Returns dict of created Jira keys to Ayon task id to link from Jira"""
    created_tasks = await _get_tasks_for_folder_id(
        project_name, folder_entity.id)
    created_tasks = {task.name: task.id for task in created_tasks}
    jira_key_to_ayon_task_id = {}
    for task_name, task_data in tasks.items():
        for key, value in task_data.items():
            if not value:
                continue
            jira_key = custom_id_to_jira_key[value]
            jira_key_to_ayon_task_id[jira_key] = created_tasks[task_name]
    return jira_key_to_ayon_task_id


def _replace_custom_ids(custom_id_to_jira_key, task_data):
    """Replaces custom id from template with real Jira id."""
    final_meta = {}
    for key, value in task_data.items():
        if key == "current_phase":
            continue
        if not value:
            continue
        jira_key = custom_id_to_jira_key.get(value)
        if jira_key:
            key = key.replace("_id", "_ticket")
            final_meta[key] = jira_key

    return final_meta


def _process_jira_template_data(
        jira_conn, project_code, jira_template_data, folder_paths):
    print("Starting JIRA processing")

    custom_id_to_task_key = {}
    tasks_created = tasks_updated = epics_created = 0
    for folder_path in folder_paths:
        folder_name = os.path.basename(folder_path)
        epics = _get_all_epics(
            jira_conn,
            project_code,
            {"Custom_ID": f"~ '{folder_name}_*'"}
        )
        epic_name_to_ids = {
            epic_info["summary"]: epic_id
            for epic_id, epic_info in epics.items()
        }

        issues = _get_all_issues(
            jira_conn,
            project_code,
            {"Custom_ID": f"~ '{folder_name}_*'"}
        )
        issues_by_custom_id = {issue["custom_id"]: issue
                               for issue in issues.values()}

        for item in jira_template_data["jira_template"]:
            epic_name = item["Epic Link"]
            epic_id = epic_name_to_ids.get(epic_name)

            custom_id = item["Custom ID"]
            folder_name = os.path.basename(folder_path)
            full_custom_id = f"{folder_name}_{custom_id}"
            if not epic_id:
                epic_id = _create_jira_epic(
                    jira_conn, project_code, item, full_custom_id)
                epic_name_to_ids[epic_name] = epic_id
                epics_created += 1

            existing_task = issues_by_custom_id.get(full_custom_id)
            task_content = _create_jira_task_content(
                full_custom_id, epic_id, item, project_code)
            if existing_task:
                task_key = existing_task["key"]
                existing_task.update(task_content)
                tasks_updated += 1
            else:
                task_key = _create_jira_task(
                    jira_conn,
                    task_content
                )
                tasks_created += 1
            custom_id_to_task_key[custom_id] = task_key

    _add_links(custom_id_to_task_key, jira_conn, jira_template_data)

    print("In Jira: ")
    print(f"Created {tasks_created} issues.")
    print(f"Updated {tasks_updated} issues.")
    print(f"Created {epics_created} epics.")
    return custom_id_to_task_key


def _create_jira_task(jira_conn, task_content):
    """Creates Jira task"""

    task = jira_conn.create_issue(task_content)
    return task["key"]


def _create_jira_task_content(full_custom_id, epic_id, item, project_code):
    task_dict = {
        "project": {"key": project_code},
        "summary": item["Summary"],
        "issuetype": {"name": "Task"},
        # "component": {"name": "Component"},
        "description": item["Description"],
        # "priority": {"name": item["Priority"]},
        COMPONENT_FIELD: item["Component"],
        CUSTOM_ID_FIELD: full_custom_id,
        # "Original Estimate": {"name": "Priority"},
        # "Int vs Ext": {"name": "Priority"},
    }
    if epic_id:
        task_dict["parent"] = {"id": epic_id}
    return task_dict


def _create_jira_epic(jira_conn, project_code, item, custom_id):
    """Creates Jira epic"""
    epic_dict = {
        "project": {"key": project_code},
        "summary": item["Epic Link"],
        "issuetype": {"name": "Epic"},
        # for querying back, summary not allowed in IN ()
        CUSTOM_ID_FIELD: custom_id,
    }
    epic = jira_conn.create_issue(epic_dict)
    return epic["id"]


def _add_links(custom_id_to_task_key, jira_conn, jira_template_data):
    """Adds 'Depends' (nonstandard) and Blocks links between Jira tasks

    TODO figure out updates
    """
    for item in jira_template_data["jira_template"]:
        task_key = custom_id_to_task_key[item["Custom ID"]]
        depends_on_id = item["Depends_On"]

        if depends_on_id:
            depends_on_ids = depends_on_id.split(",")
            for depends_on_id in depends_on_ids:
                depends_on_id = depends_on_id.strip()
                if not depends_on_id:
                    continue
                depends_on_key = custom_id_to_task_key[depends_on_id]
                link_dict = {
                    "type": {"name": "Depends"},
                    "inwardIssue": {"key": task_key},
                    "outwardIssue": {"key": depends_on_key},
                }
                jira_conn.create_issue_link(link_dict)

        blocks_id = item["Unblocks"]

        if blocks_id:
            blocks_ids = blocks_id.split(",")
            for blocks_id in blocks_ids:
                blocks_id = blocks_id.strip()
                if not blocks_id:
                    continue
                blocks_key = custom_id_to_task_key[blocks_id]
                link_dict = {
                    "type": {"name": "Blocks"},
                    "inwardIssue": {"key": task_key},
                    "outwardIssue": {"key": blocks_key},
                }
                jira_conn.create_issue_link(link_dict)


def _get_all_epics(jira_conn, project_code, kwargs=None):
    """Gets all epics for project code.

    TODO loop through pagination
    """
    jql_request = (f"project = '{project_code}' AND "
                    "issuetype = Epic ")

    jql_request += _add_additional_arguments(kwargs)

    content = jira_conn.jql(jql_request)
    epics = {}
    for epic in content["issues"]:
        epics[epic["id"]] = {
            "key": epic["key"],
            "summary": epic["fields"]["summary"]
        }
    return epics


def _get_all_issues(jira_conn, project_code, kwargs=None):
    """Query Jira for all issues in project with `project_code`

    Currently used only for development to learn custom fields.
    """
    jql_request = (f"project = '{project_code}' AND "
                   f"issuetype = Task")

    jql_request += _add_additional_arguments(kwargs)

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


def _add_additional_arguments(kwargs):
    """Allows to add AND arguments.

    It expects dictionary, where values:
        ('a', 'b', 'c)
        '~ 'Value*''
        '= 'Value''
    """
    additional_filter = ""
    if kwargs:
        for key, value in kwargs.items():
            if isinstance(value, set) or isinstance(value, list):
                quoted_values = ', '.join(f'"{val}"' for val in value)
                additional_filter += f" AND {key} in ({quoted_values})"
            else:
                additional_filter += f" AND {key} {value}"
    return additional_filter


def _get_ayon_template_data(template_name, placeholder_map):
    """Returns processed content of AYON template as dict"""
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


def _convert_task_type(task_type):
    """Converts non-existent task types.

    Should be queried from Server.
    """
    convert_tasks = {"Concept": "Generic",
                     "Model": "Modeling"}

    if task_type in convert_tasks:
        return convert_tasks[task_type]
    return task_type


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


async def _get_folder_by_path(project_name, folder_path):
    res = await Postgres.fetch(
        f"SELECT id FROM project_{project_name}.hierarchy WHERE path = $1",
        folder_path)
    if not res:
        raise NotFoundException
    folder_id = res[0]["id"]
    folder = await FolderEntity.load(project_name, folder_id)
    return folder


async def _get_tasks_for_folder_id(project_name, folder_id):
    res = await Postgres.fetch(
        f"SELECT id FROM project_{project_name}.tasks "
        f"WHERE folder_id = $1", folder_id)

    tasks = []

    for rec in res:
        task_id = rec["id"]
        task = await TaskEntity.load(project_name, task_id)
        tasks.append(task)

    return tasks


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
