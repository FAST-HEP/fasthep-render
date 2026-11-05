import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { middleTruncate, recorded } from "../model/format";
import { type TreeRow, toRows } from "../model/valueTree";

function Row({ row, depth }: { row: TreeRow; depth: number }) {
  const [open, setOpen] = useState(false);
  const expandable = !!row.children?.length;
  return (
    <>
      <tr>
        <th scope="row" style={{ paddingLeft: `${0.4 + depth * 0.9}rem` }} title={row.key}>
          {expandable ? (
            <button type="button" className="twisty" aria-expanded={open} onClick={() => setOpen(!open)}>
              <ChevronRight size={14} className={open ? "open" : ""} aria-hidden="true" />
              <span>{row.key}</span>
            </button>
          ) : (
            <span>{row.key}</span>
          )}
        </th>
        <td title={row.full}>{middleTruncate(row.text)}</td>
      </tr>
      {open && row.children?.map((c) => <Row key={c.key} row={c} depth={depth + 1} />)}
    </>
  );
}

/**
 * A recorded value as a key/value table. Nested values start collapsed with a summary
 * ("[2 items]"), long values are shortened with the full text on hover.
 * Missing (`undefined`) is "Not recorded"; null inside a value is shown as `null`.
 */
export function ValueTree({ value }: { value: unknown }) {
  if (value === undefined || value === null) return <div className="notrec">{recorded(value)}</div>;
  const rows = toRows(value);
  if (rows.length === 0) return <div className="notrec">{recorded(Array.isArray(value) ? [] : "")}</div>;
  return (
    <table className="valuetree">
      <tbody>
        {rows.map((r) => (
          <Row key={r.key} row={r} depth={0} />
        ))}
      </tbody>
    </table>
  );
}
