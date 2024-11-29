import React, { useContext, useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import Jira from "./Jira";
import { AddonProvider, AddonContext } from "@ynput/ayon-react-addon-provider";
import axios from "axios";

import "@ynput/ayon-react-components/dist/style.css";
import "./index.scss";

const App = () => {
  const context = useContext(AddonContext);
  const standAlone = context.standAlone;
  const addonName = standAlone ? "jira" : context.addonName;
  const addonVersion = standAlone ? "0.1.1" : context.addonVersion;
  const accessToken = useContext(AddonContext).accessToken;
  const projectName = useContext(AddonContext).projectName;
  const [tokenSet, setTokenSet] = useState(false);

  useEffect(() => {
    if (accessToken && !tokenSet) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`;
      setTokenSet(true);
    }
  }, [accessToken, tokenSet]);

  return (
    <Jira
      context={context}
      addonName={addonName}
      addonVersion={addonVersion}
      accessToken={accessToken}
      projectName={projectName}
    />
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AddonProvider debug>
      <App />
    </AddonProvider>
  </React.StrictMode>
);
