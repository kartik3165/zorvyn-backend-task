import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../config/api-client";

export const loginUser = createAsyncThunk(
    "auth/login",
    async (credentials, { rejectWithValue }) => {
        try {
            await apiClient.post("/auth/login", credentials);
            // Fetch user info directly after login because login response might not contain it
            const { data } = await apiClient.get("/auth/me");
            return data.data; // unwrap StandardResponse
        } catch (error) {
            return rejectWithValue(error.message || "Login failed");
        }
    }
);

// Named fetchUser to match the dispatch call in app/app.jsx
export const fetchUser = createAsyncThunk("auth/fetchUser", async (_, { rejectWithValue }) => {
    try {
        const { data } = await apiClient.get("/auth/me");
        return data.data; // unwrap StandardResponse
    } catch (error) {
        return rejectWithValue(error.message || null);
    }
});

export const logoutThunk = createAsyncThunk("auth/logout", async (_, { rejectWithValue }) => {
    try {
        await apiClient.post("/auth/logout");
    } catch (error) {
        return rejectWithValue(error.message || "Logout failed");
    }
});

const authSlice = createSlice({
    name: "auth",
    initialState: {
        user: null,
        loading: true,
        initialized: false, // router.jsx gates render on this
        error: null,
    },
    reducers: {
        setUser(state, action) {
            state.user = action.payload;
            state.loading = false;
            state.initialized = true;
        },
        clearUser(state) {
            state.user = null;
            state.loading = false;
            state.initialized = true;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchUser.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(loginUser.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(loginUser.fulfilled, (state, action) => {
                state.user = action.payload;
                state.loading = false;
                state.initialized = true;
                state.error = null;
            })
            .addCase(loginUser.rejected, (state, action) => {
                state.user = null;
                state.loading = false;
                state.initialized = true;
                state.error = action.payload || "Login failed";
            })
            .addCase(fetchUser.fulfilled, (state, action) => {
                state.user = action.payload;
                state.loading = false;
                state.initialized = true;
                state.error = null;
            })
            .addCase(fetchUser.rejected, (state, action) => {
                state.user = null;
                state.loading = false;
                state.initialized = true; // still done, just not authed
                state.error = action.payload || null;
            })
            .addCase(logoutThunk.fulfilled, (state) => {
                state.user = null;
                state.loading = false;
                state.initialized = true;
                state.error = null;
            })
            .addCase(logoutThunk.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload || "Logout failed";
            });
    },
});

export const { setUser, clearUser } = authSlice.actions;
export default authSlice.reducer;
