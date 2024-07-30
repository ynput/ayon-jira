import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  Dropdown,
  Icon,
  InputText,
  SaveButton,
} from "@ynput/ayon-react-components";
import * as Styled from "./Jira.styled";

const Jira = ({ projectName, addonName, addonVersion }) => {
  const [loading, setLoading] = useState(false);

  const [templates, setTemplates] = useState();
  const [folderPath, setFolderPath] = useState();
  const [jiraProjectCode, setJiraProjectCode] = useState();
  const [selectedTemplate, setSelectedTemplate] = useState();

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    const endpoint = `/api/addons/${addonName}/${addonVersion}/get_templates`;
    try {
      const response = await axios.get(endpoint);
      let templates = [];
      for (const template_name of response.data) {
        templates.push({ name: template_name, value: template_name });
      }
      setTemplates(templates);
      setError(null);
    } catch (error) {
      console.error("Error fetching templates:", error);
      setError(error.response.data.detail);
    } finally {
      setLoading(false);
    }
  }, [addonName, addonVersion, setLoading, setTemplates]);

  useEffect(() => {
    if (!projectName || !addonName || !addonVersion) return;

    fetchTemplates();
  }, [projectName, addonName, addonVersion, fetchTemplates]);

  const create = async () => {
    setCreating(true);
    const endpoint = `/api/addons/${addonName}/${addonVersion}/run_template`;

    const payload = {
      project_name: projectName,
      jira_project_code: jiraProjectCode,
      template_name: selectedTemplate,
      folder_paths: [folderPath],
      placeholder_map: {
        // TODO
        Tier1CharacterNameOutfitName: "Character1",
        Tier1CharacterName: "Character1",
      },
    };
    console.log("payload", payload);

    try {
      await axios.post(endpoint, payload);
      setError(null);
      setSuccess(true);

      // remove success message after 5 seconds
      setTimeout(() => {
        setSuccess(false);
      }, 1000);
    } catch (error) {
      setSuccess(false);
      setError(error.response.data.detail);
      console.error("Error running template:", error);
    } finally {
      setCreating(false);
      onClear();
    }
  };

  const onClear = () => {
    setFolderPath("");
    setJiraProjectCode("");
    setSelectedTemplate("");
  };

  const validateForm = () => folderPath && jiraProjectCode && selectedTemplate;

  return (
    <Styled.Container>
      <div>
        <h2>New Task</h2>
        <p>Creates a new AYON task and synced Jira ticket.</p>
      </div>
      <Styled.Form className={loading ? "loading" : ""}>
        <label>Folder Path</label>
        <InputText
          id="folderPath"
          name="folderPath"
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          disabled={creating}
        />
        <label>Jira Project Code</label>
        <InputText
          id="jiraProjectCode"
          name="jiraProjectCode"
          value={jiraProjectCode}
          onChange={(e) => setJiraProjectCode(e.target.value)}
          disabled={creating}
          autoComplete="off"
        />
        <label>Template</label>
        <Dropdown
          value={[selectedTemplate]}
          options={templates}
          optionLabel="name"
          onChange={(value) => setSelectedTemplate(value[0])}
          placeholder="Select template"
          className={"template-dropdown"}
          onClick={(e) => e.stopPropagation()}
          disabled={creating || loading}
        />
      </Styled.Form>
      {error && (
        <Styled.Error>
          <Icon icon="error" />
          {error}
        </Styled.Error>
      )}
      {success && (
        <Styled.Success>
          <Icon icon="check_circle" />
          Task and ticket created!
        </Styled.Success>
      )}
      <SaveButton
        className="save"
        label="Create"
        icon="send"
        onClick={create}
        active={validateForm()}
        saving={creating}
      />
    </Styled.Container>
  );
};

export default Jira;
