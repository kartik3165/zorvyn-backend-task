import { toast, Bounce } from "react-toastify";

const baseConfig = {
    position: "top-right",
    autoClose: 4000,
    theme: "dark",
    transition: Bounce,
};

export const showSuccess = (message) =>
    toast.success(message, baseConfig);

export const showError = (message) =>
    toast.error(message, baseConfig);

export const showInfo = (message) =>
    toast.info(message, baseConfig);

export { toast };
