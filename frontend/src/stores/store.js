import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";

// Named export — matches: import { store } from "../stores/store" in provider.jsx
export const store = configureStore({
    reducer: {
        auth: authReducer,
    },
});

export default store;