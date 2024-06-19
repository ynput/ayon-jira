// My React App.

import AYONLogo from "./assets/ayon.svg";
import React, { useState } from "react";
import "./App.css";


function App() {
  const [count, setCount] = useState(0);

  return (
      <>
      <div class="form-container">
        <form action="#">
          <label for="folderPath">Folder Path:</label>
          <input type="text" id="folderPath" name="folderPath" required />

          <label for="jiraProjectCode">Jira Project Code:</label>
          <input type="text" id="jiraProjectCode" name="jiraProjectCode" required />

          <label for="template">Template:</label>
          <select name="template" id="template">
            <option value="">Select Template</option>  <option value="template1">Template 1</option>
            <option value="template2">Template 2</option>
            </select>

          <button type="submit">Create</button>
        </form>
      </div>
      </>
  );
}

export default App;
