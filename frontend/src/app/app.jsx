import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { fetchUser } from "../stores/authSlice";
import AppRouter from "./router";

export default function App() {
    const dispatch = useDispatch();

    useEffect(() => {
        dispatch(fetchUser());
    }, [dispatch]);

    return <AppRouter />;
}
