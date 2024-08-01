import { Icon, InputText } from "@ynput/ayon-react-components";
import axios from "axios";
import styled from "styled-components";

const StyledRow = styled.div`
  position: relative;
  input {
    width: 100%;
    padding-right: 32px;
  }
  .icon {
    position: absolute;
    right: 8px;
    top: 50%;
    translate: 0 -50%;

    cursor: pointer;
  }
`;

const GET_FOLDER_PATH_QUERY = `
query GetFolderPath($projectName: String!, $entityId: String!) {
  project(name: $projectName) {
    folder(id: $entityId) {
      id
      path
    }
  }
}

`;

const PathInput = ({ onSelect, projectName, ...props }) => {
  // get folder path for the folder id
  const onFolderSelect = async (id) => {
    try {
      const response = await axios.post(`/graphql`, {
        query: GET_FOLDER_PATH_QUERY,
        variables: { projectName, entityId: id },
      });

      const path = response.data.data.project.folder.path;

      onSelect(path);
    } catch (error) {
      console.error(error);
    }
  };

  const handlePicker = () => {
    window.parent.modalRequest("folderPicker", (id) => onFolderSelect(id));
  };

  return (
    <StyledRow>
      <InputText {...props} />
      <Icon icon="colorize" onClick={handlePicker} />
    </StyledRow>
  );
};

export default PathInput;
