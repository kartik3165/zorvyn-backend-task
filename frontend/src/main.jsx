import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./app/app";
import { AppProvider } from "./app/provider";

ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <AppProvider>
            <App />
        </AppProvider>
    </React.StrictMode>
);