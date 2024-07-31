import { useState, useEffect, useCallback, Fragment } from "react";
import axios from "axios";
import {
  Dropdown,
  Icon,
  InputText,
  SaveButton,
  Dialog
} from "@ynput/ayon-react-components";
import * as Styled from "./Jira.styled";
import dummy_data from "./dummy_data";

const Jira = ({ projectName, addonName, addonVersion }) => {
  const [loading, setLoading] = useState(false);

  const [templates, setTemplates] = useState([]);
  const [folderPath, setFolderPath] = useState("");
  const [jiraProjectCode, setJiraProjectCode] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState(null);

  // what fields to show based on selected template
  const [templateFields, setTemplateFields] = useState([]);
  // the input data for the fields
  const [templateFieldsForm, setTemplateFieldsForm] = useState({});

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [processFinished, setProcessFinished] = useState(false)
  const [responseContent, setResponseContent] = useState(null);

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
      placeholder_map: templateFieldsForm,
    };
    console.log("payload", payload);

    try {
      content = await axios.post(endpoint, payload);
      setResponseContent(content)
      setError(null);
      setSuccess(true);

      // remove success message after 5 seconds
      setTimeout(() => {
        setSuccess(false);
      }, 1000);
    } catch (error) {
      setSuccess(false);
      setError(error.response.data.detail);
      setResponseContent(error.response.data.detail)
      console.error("Error running template:", error);
    } finally {
      setProcessFinished(true);
      setCreating(false);
      onClear();
    }
  };

  const handleTemplateChange = async (values = []) => {
    const template_name = values[0]
    setSelectedTemplate(template_name);

    // set dynamic fields based on selected template
    const endpoint = `/api/addons/${addonName}/${addonVersion}/get_placeholders?template_name=${template_name}`;

    try {
      const response = await axios.get(endpoint);
      let placeholders = [];
      for (const placeholder of response.data) {
        placeholders.push({"id": placeholder, "label": placeholder});
      }
      setTemplateFields(placeholders)
      setError(null);

      const templateFieldsForm = {};
      placeholders.forEach((placeholder, index) => {
        let value = "";
        // parse out last part from folder path if available as first
        // placeholder would be asset name, most likely
        if (index === 0) {
            if (folderPath){
              const lastPart = folderPath.split('/').pop();
              value = lastPart;
            }
        }
        templateFieldsForm[placeholder.id] = value;
      });
      setTemplateFieldsForm(templateFieldsForm);
    } catch (error) {
      console.error("Error fetching placeholders:", error);
      setError(error.response.data.detail);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateFieldChange = (e) => {
    const target = e.target;
    const { id, value } = target;

    setTemplateFieldsForm((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  const onClear = () => {
    setFolderPath("");
    setJiraProjectCode("");
    setSelectedTemplate("");
    setTemplateFields([]);
    setTemplateFieldsForm({});
  };

  const validateForm = () => {
    const baseValidated = folderPath && jiraProjectCode && selectedTemplate;
    const fieldsValidated = templateFields.every(
      ({ id, required }) => !required || templateFieldsForm[id]
    );

    return baseValidated && fieldsValidated;
  };

  return (
    <>
       <Dialog
          isOpen={processFinished}
          header={'Process finished'}
          onClose={onClear}
          size="md"
       >
            <div>{responseContent}</div>
       </Dialog>
       <Styled.Container>
          <div>
            <h2>New Tasks</h2>
            <p>Creates a new AYON tasks and synced Jira tickets.</p>
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
              onChange={handleTemplateChange}
              placeholder="Select template"
              className={"template-dropdown"}
              onClick={(e) => e.stopPropagation()}
              disabled={creating || loading}
            />
            {templateFields.map(({ id, label, ...props }) => (
              <Fragment key={id}>
                <label>{label}</label>
                <InputText
                  id={id}
                  name={id}
                  value={templateFieldsForm[id]}
                  onChange={handleTemplateFieldChange}
                  disabled={creating}
                  autoComplete="off"
                  {...props}
                  required={false}
                />
              </Fragment>
            ))}
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
    </>
  );
};

export default Jira;
