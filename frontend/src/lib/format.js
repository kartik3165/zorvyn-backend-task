export const formatCurrency = (value) =>
    new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
    }).format(value);

export function formatDate(iso) {
    if (!iso) return "—";
    // Slice the date part directly — avoids UTC↔local conversion entirely
    const [year, month, day] = iso.split("T")[0].split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}