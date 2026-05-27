import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// Auto-redirect user app to correct hash route
if (window.location.pathname.startsWith("/app") && !window.location.hash.startsWith("#/app")) {
  window.location.replace("/app/#/app");
}
if (window.location.pathname.startsWith("/manage") && !window.location.hash.startsWith("#/")) {
  window.location.replace("/manage/#/");
}

import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found");

ReactDOM.createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
