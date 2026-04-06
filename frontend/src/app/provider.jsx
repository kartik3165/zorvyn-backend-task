import { Provider } from "react-redux";
import { store } from "../stores/store";

export function AppProvider({ children }) {
    return (
        <Provider store={store}>
            {children}
        </Provider>
    );
}
