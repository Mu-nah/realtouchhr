import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Suppress MetaMask / wallet extension errors that leak into the React error overlay
window.addEventListener('error', (e) => {
    if (e?.message?.includes('MetaMask') || e?.filename?.includes('chrome-extension')) {
        e.stopImmediatePropagation();
        e.preventDefault();
    }
});
window.addEventListener('unhandledrejection', (e) => {
    const msg = e?.reason?.message || '';
    if (msg.includes('MetaMask') || msg.includes('chrome-extension')) {
        e.stopImmediatePropagation();
        e.preventDefault();
    }
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
