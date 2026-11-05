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

/**
 * Shorten a long value in the middle, keeping both ends: for dotted paths such as
 * `fasthep_carpenter.operations.hist:run_hist_transform` the end names the callable.
 * The full text belongs in a hover title.
 */
export function middleTruncate(text: string, max = 30): string {
  if (text.length <= max) return text;
  const tail = Math.ceil((max - 1) * 0.65);
  const head = max - 1 - tail;
  return `${text.slice(0, head)}…${text.slice(text.length - tail)}`;
}
