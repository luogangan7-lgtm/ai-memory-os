import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// Auto-redirect user app to correct hash route
if (window.location.pathname.startsWith("/app")) {
  window.location.replace("/app/#/app");
}

import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found");

ReactDOM.createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
