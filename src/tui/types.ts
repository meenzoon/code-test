export type EntryKind =
  | "user"
  | "assistant"
  | "tool_call"
  | "tool_result"
  | "tool_error"
  | "error"
  | "info";

export interface ChatEntry {
  id: string;
  kind: EntryKind;
  content: string;
  meta?: string; // tool name, model, etc.
  timestamp: Date;
}
