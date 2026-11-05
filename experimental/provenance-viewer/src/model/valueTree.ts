// Nested recorded values (parameters, operations, meta) as rows a panel can show as a
// table with expandable nesting. Pure; no React.

export interface TreeRow {
  key: string;
  /** What the value cell shows: the scalar itself, or a summary of a container. */
  text: string;
  /** The complete text, for a hover title when `text` is shortened. */
  full: string;
  children?: TreeRow[];
}

const MAX_INLINE_ITEMS = 6;

function scalarText(v: unknown): string {
  if (v === null) return "null";
  if (v === "") return "(empty)";
  return String(v);
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** An array item of objects is named by its `name`, `id` or `node_id`, else by its index. */
function itemKey(item: unknown, index: number): string {
  if (isObject(item)) {
    for (const k of ["name", "id", "node_id"]) {
      if (typeof item[k] === "string" && item[k]) return item[k] as string;
    }
  }
  return `[${index}]`;
}

function summarise(v: unknown): string {
  if (Array.isArray(v)) {
    const inline = v.every((x) => !(typeof x === "object" && x !== null));
    if (inline && v.length > 0 && v.length <= MAX_INLINE_ITEMS) return v.map(scalarText).join(", ");
    return `[${v.length} item${v.length === 1 ? "" : "s"}]`;
  }
  if (isObject(v)) {
    const n = Object.keys(v).length;
    return n === 0 ? "{}" : `{${n} key${n === 1 ? "" : "s"}}`;
  }
  return scalarText(v);
}

function full(v: unknown): string {
  return typeof v === "object" && v !== null ? JSON.stringify(v) : scalarText(v);
}

export function toRows(value: unknown): TreeRow[] {
  const rowOf = (key: string, v: unknown): TreeRow => {
    const inlineArray = Array.isArray(v) && summarise(v).indexOf("[") !== 0;
    const row: TreeRow = { key, text: summarise(v), full: full(v) };
    if (!inlineArray && Array.isArray(v) && v.length) row.children = v.map((x, i) => rowOf(itemKey(x, i), x));
    else if (isObject(v) && Object.keys(v).length) row.children = Object.entries(v).map(([k, x]) => rowOf(k, x));
    return row;
  };
  if (isObject(value)) return Object.entries(value).map(([k, v]) => rowOf(k, v));
  if (Array.isArray(value)) return value.map((x, i) => rowOf(itemKey(x, i), x));
  return value === undefined ? [] : [{ key: "value", text: scalarText(value), full: scalarText(value) }];
}
