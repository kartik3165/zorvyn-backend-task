// DashboardPage is now a thin shell.
// AppShell owns the layout + sidebar. This file exists so the router import still resolves.
// router.jsx now points directly to AppShell — this file is no longer needed,
// but kept here in case you reference it elsewhere.

export { default } from "../AppShell";