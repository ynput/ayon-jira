import { useState, useEffect } from 'react'
import axios from 'axios'
import { Dropdown } from 'primereact/dropdown';
import { Button, FormRow, InputText, Panel, SaveButton, Spacer } from '@ynput/ayon-react-components'


const JiraPage = ({projectName, addonName, addonVersion}) => {
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState()
  const [folderPath, setFolderPath] = useState()
  const [jiraProjectCode, setJiraProjectCode] = useState()
  const [selectedTemplate, setSelectedTemplate] = useState()

  useEffect(() => {
    if (!projectName || !addonName || !addonVersion)
      return

    setLoading(true)

    const endpoint = `/api/addons/${addonName}/${addonVersion}/get_templates`
    axios
      .get(endpoint)
      .then((response) => {
        let templates = []
        for (const template_name of response.data){
            templates.push({ name: template_name, value: template_name })
        }
        setTemplates(templates)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [projectName])

  const create = () => {

    const endpoint = `/api/addons/${addonName}/${addonVersion}/run_template`

    const payload = {
        "project_name": projectName,
        "jira_project_code": jiraProjectCode,
        "template_name": selectedTemplate,
        "folder_paths": [folderPath],
        "placeholder_map": {  // TODO
            "Tier1CharacterNameOutfitName": "Character1",
            "Tier1CharacterName": "Character1"
        }

    }
    console.log('payload', payload)
    axios
      .post(endpoint, payload)
      .then((response) => {
      })
      .finally(() => {
        setLoading(false)
      })
    onClear()
  }

  const onClear = () => {
    setFolderPath("")
    setJiraProjectCode("")
    setSelectedTemplate("")
  }


  return (
      <div className="flex flex-wrap align-items-center mb-3 gap-2">
        <form action="#">
            <FormRow label="Folder Path:">
              <label for="folderPath">Folder Path:</label>
              <InputText id="folderPath"
                    name="folderPath"
                    value={folderPath}
                    onChange={(e) => setFolderPath(e.target.value)}
                    required />
            </FormRow>
            <FormRow label="Jira Project Code:">
              <label for="jiraProjectCode">Jira Project Code:</label>
              <InputText id="jiraProjectCode"
                    name="jiraProjectCode"
                    value={jiraProjectCode}
                    onChange={(e) => setJiraProjectCode(e.target.value)}
                    required />
            </FormRow>
            <FormRow label="Select Template">
              <Dropdown
                value={selectedTemplate}
                options={templates} optionLabel="name"
                onChange={(e) => setSelectedTemplate(e.value)}
                placeholder="Select template" className="w-full md:w-14rem" />

              <SaveButton
                label="Create"
                icon="send"
                onClick={create}
                active={folderPath && jiraProjectCode && selectedTemplate}
              />
            </FormRow>
        </form>
      </div>
  )
}

export default JiraPage
