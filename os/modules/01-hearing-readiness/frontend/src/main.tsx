import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App";
import { I18nProvider } from "./i18n";
import { LowBandwidthProvider } from "./lib/lowBandwidth";
import { SelectedCaseProvider } from "./lib/selectedCase";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <LowBandwidthProvider>
        <BrowserRouter>
          <SelectedCaseProvider>
            <App />
          </SelectedCaseProvider>
        </BrowserRouter>
      </LowBandwidthProvider>
    </I18nProvider>
  </StrictMode>
);
