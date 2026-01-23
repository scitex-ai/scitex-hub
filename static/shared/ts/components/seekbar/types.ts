/**
 * Seekbar Type Definitions
 * Extracted from seekbar.ts for modularity
 */

/** Seekbar values */
export interface SeekbarValues {
  min: number;
  max: number;
}

/** Value formatter function */
export type FormatFunction = (value: number) => string;

/** Callback for value changes */
export type ValueCallback = (values: SeekbarValues) => void;

/** Handle type */
export type HandleType = "min" | "max";

/** Seekbar configuration options */
export interface SeekbarOptions {
  /** Minimum value (default: 0) */
  min?: number;
  /** Maximum value (default: 100) */
  max?: number;
  /** Initial minimum value */
  valueMin?: number;
  /** Initial maximum value */
  valueMax?: number;
  /** Step increment (default: 1) */
  step?: number;
  /** Value formatting function */
  format?: FormatFunction;
  /** Called when value changes */
  onChange?: ValueCallback | null;
  /** Called during drag */
  onUpdate?: ValueCallback | null;
  /** Called when drag starts */
  onStart?: ValueCallback | null;
  /** Called when drag ends */
  onEnd?: ValueCallback | null;
  /** Show value labels on hover (default: true) */
  showLabels?: boolean;
  /** Show value display below (default: false) */
  showValues?: boolean;
}

/** Internal elements references */
export interface SeekbarElements {
  container: HTMLDivElement;
  track: HTMLDivElement;
  range: HTMLDivElement;
  handleMin: HTMLDivElement;
  handleMax: HTMLDivElement;
  labelMin: HTMLDivElement | null;
  labelMax: HTMLDivElement | null;
  valueMin?: HTMLSpanElement;
  valueMax?: HTMLSpanElement;
}

/** Complete options with defaults applied */
export interface CompleteSeekbarOptions
  extends Required<
    Omit<SeekbarOptions, "onChange" | "onUpdate" | "onStart" | "onEnd">
  > {
  onChange: ValueCallback | null;
  onUpdate: ValueCallback | null;
  onStart: ValueCallback | null;
  onEnd: ValueCallback | null;
}
