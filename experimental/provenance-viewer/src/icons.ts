// One place that maps every kind of thing the viewer shows to an icon and a plain label.
// Icons are from lucide-react (ISC licence, compatible with BSD); swapping one is a one-line change here.

import {
  ArrowRightFromLine,
  ArrowRightToLine,
  Boxes,
  ChartColumn,
  ChartLine,
  CircleCheck,
  CircleDashed,
  CircleHelp,
  CircleOff,
  Cog,
  Database,
  Eye,
  File,
  FileInput,
  Funnel,
  HardDriveDownload,
  Layers,
  type LucideIcon,
  Split,
  Table,
} from "lucide-react";
import type { Completeness, VisibleEntity } from "./model/types";

export function entityIcon(e: VisibleEntity): LucideIcon {
  switch (e.kind) {
    case "dataset":
      return Database;
    case "boundary":
      return e.direction === "in" ? ArrowRightToLine : ArrowRightFromLine;
    case "summary":
      return { chain: Layers, variation_family: Boxes, variation: Split, datasets: Database, region: Boxes }[e.groupKind];
    case "processing":
      return { source: FileInput, transform: Cog, sink: HardDriveDownload, observer: Eye }[e.role] ?? Cog;
  }
}

export function entityTypeLabel(e: VisibleEntity): string {
  switch (e.kind) {
    case "dataset":
      return "Dataset";
    case "boundary":
      return e.direction === "in" ? "Enters from outside the focused group" : "Leaves to outside the focused group";
    case "summary":
      return e.linear ? "Hidden linear steps" : "Hidden group";
    case "processing":
      return { source: "Source", transform: "Transform", sink: "Sink", observer: "Observer" }[e.role] ?? e.role;
  }
}

export function artifactIcon(kind: string): LucideIcon {
  return { histogram: ChartColumn, plot: ChartLine, cutflow: Funnel, table: Table }[kind] ?? File;
}

export function completenessIcon(c: Completeness): LucideIcon {
  return { complete: CircleCheck, partial: CircleDashed, unavailable: CircleOff, not_recorded: CircleHelp }[c];
}
