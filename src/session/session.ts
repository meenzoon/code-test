import {
  streamText,
  type CoreMessage,
  type LanguageModelV1,
  type TextStreamPart,
  type ToolCallPart,
  type ToolResultPart,
} from "ai";
import type { Tools } from "../tools/index.js";

export type MessageRole = "user" | "assistant" | "system";

export interface SessionEvent {
  type:
    | "text_delta"
    | "tool_call"
    | "tool_result"
    | "error"
    | "done"
    | "step_done";
  content?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolResult?: string;
  isError?: boolean;
}

export type EventHandler = (event: SessionEvent) => void;

/**
 * Session manages conversation history and drives the agentic loop:
 *   user message → LLM stream → tool calls → tool execution → LLM stream → ...
 */
export class Session {
  private messages: CoreMessage[] = [];
  private model: LanguageModelV1;
  private tools: Tools;
  private systemPrompt: string;
  private onEvent?: EventHandler;

  constructor(options: {
    model: LanguageModelV1;
    tools: Tools;
    systemPrompt: string;
    onEvent?: EventHandler;
  }) {
    this.model = options.model;
    this.tools = options.tools;
    this.systemPrompt = options.systemPrompt;
    this.onEvent = options.onEvent;
  }

  setEventHandler(handler: EventHandler) {
    this.onEvent = handler;
  }

  getMessages(): CoreMessage[] {
    return this.messages;
  }

  clearHistory() {
    this.messages = [];
  }

  async send(userMessage: string): Promise<void> {
    this.messages.push({ role: "user", content: userMessage });
    await this.runTurn();
  }

  private emit(event: SessionEvent) {
    this.onEvent?.(event);
  }

  private async runTurn(): Promise<void> {
    try {
      const result = streamText({
        model: this.model,
        system: this.systemPrompt,
        messages: this.messages,
        tools: this.tools,
        maxSteps: 20, // Vercel AI SDK handles the agentic loop automatically
        onChunk: ({ chunk }) => {
          if (chunk.type === "text-delta") {
            this.emit({ type: "text_delta", content: chunk.textDelta });
          } else if (chunk.type === "tool-call") {
            this.emit({
              type: "tool_call",
              toolName: chunk.toolName,
              toolInput: chunk.args as Record<string, unknown>,
            });
          } else if (chunk.type === "tool-result") {
            const resultText =
              typeof chunk.result === "string"
                ? chunk.result
                : JSON.stringify(chunk.result);
            this.emit({
              type: "tool_result",
              toolName: chunk.toolName,
              toolResult: resultText,
              isError: false,
            });
          }
        },
        onError: ({ error }) => {
          this.emit({
            type: "error",
            content: error instanceof Error ? error.message : String(error),
          });
        },
        onFinish: ({ response }) => {
          // Append all response messages to history
          this.messages.push(...response.messages);
          this.emit({ type: "done" });
        },
      });

      // Consume the stream (required to trigger callbacks)
      await result.consumeStream();
    } catch (e) {
      this.emit({
        type: "error",
        content: e instanceof Error ? e.message : String(e),
      });
    }
  }

  /** Save session to JSON */
  toJSON(): string {
    return JSON.stringify(
      { messages: this.messages, systemPrompt: this.systemPrompt },
      null,
      2
    );
  }

  /** Load messages from a previous session JSON */
  loadJSON(json: string) {
    const data = JSON.parse(json);
    this.messages = data.messages ?? [];
  }
}
