/**
 * Lightweight className joiner — no clsx/tailwind-merge needed.
 */
export function cn(...inputs) {
  return inputs
    .flat(Infinity)
    .filter((x) => x && typeof x === "string")
    .join(" ")
    .trim();
}
