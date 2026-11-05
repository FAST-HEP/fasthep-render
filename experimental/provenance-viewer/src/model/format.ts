/**
 * Missing and empty are different facts. `undefined` and `null` were not recorded;
 * an empty string or list was recorded as empty. Used by every panel and the text view.
 */
export function recorded(value: unknown): string {
  if (value === undefined || value === null) return "Not recorded";
  if (value === "" || (Array.isArray(value) && value.length === 0)) return "(empty)";
  return String(value);
}

/** "1 step hidden" / "2 steps hidden" / "1 entity hidden". */
export function hiddenLabel(count: number, linear: boolean): string {
  const unit = linear ? (count === 1 ? "step" : "steps") : count === 1 ? "entity" : "entities";
  return `${count} ${unit} hidden`;
}
