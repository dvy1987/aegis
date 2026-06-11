/**
 * Tuned icon set for Heuristics.
 *
 * Functional icons go through `tuneLucide` so stroke / linecap / size
 * follow the design system. Bespoke SVGs (denial, appeal, deadline,
 * evidence, etc.) will be added as React components alongside this file
 * during T1.3+ — see `.design/aegis/ICONS.md` for the inventory.
 */

import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  ChevronDown,
  Copy,
  Download,
  Pencil,
  Search,
  Settings,
  X,
} from "lucide-react";

import { tuneLucide } from "./lucide";

export const ArrowRightIcon = tuneLucide(ArrowRight);
export const ArrowUpRightIcon = tuneLucide(ArrowUpRight);
export const CheckIcon = tuneLucide(Check);
export const ChevronRightIcon = tuneLucide(ChevronRight);
export const ChevronDownIcon = tuneLucide(ChevronDown);
export const CopyIcon = tuneLucide(Copy);
export const DownloadIcon = tuneLucide(Download);
export const PencilIcon = tuneLucide(Pencil);
export const SearchIcon = tuneLucide(Search);
export const SettingsIcon = tuneLucide(Settings);
export const CloseIcon = tuneLucide(X);
