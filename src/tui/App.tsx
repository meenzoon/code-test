import React, { useState, useCallback, useEffect, useRef } from "react";
import { Box, Text, useInput, useApp, useStdout } from "ink";
import TextInput from "ink-text-input";
import Spinner from "ink-spinner";
import type { Config } from "../config/config.js";
import type { Session } from "../session/session.js";
import type { SessionEvent } from "../session/session.js";
import { MessageItem } from "./MessageItem.js";
import type { ChatEntry, EntryKind } from "./types.js";

interface Props {
  config: Config;
  session: Session;
}

let entryCounter = 0;
function makeEntry(
  kind: EntryKind,
  content: string,
  meta?: string
): ChatEntry {
  return { id: String(entryCounter++), kind, content, meta, timestamp: new Date() };
}

export function App({ config, session }: Props) {
  const { exit } = useApp();
  const { stdout } = useStdout();
  const width = stdout?.columns ?? 100;

  const [entries, setEntries] = useState<ChatEntry[]>([
    makeEntry(
      "info",
      `CodeGen ready — provider: ${config.llm.provider}  model: ${config.llm.model}  workDir: ${config.workDir}`
    ),
    makeEntry("info", "Type a message and press Enter. Ctrl+C to quit."),
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");

  // Scroll: we track number of visible entries
  const [scrollOffset, setScrollOffset] = useState(0);

  const appendEntry = useCallback((entry: ChatEntry) => {
    setEntries((prev) => [...prev, entry]);
  }, []);

  // Wire session events
  useEffect(() => {
    session.setEventHandler((event: SessionEvent) => {
      switch (event.type) {
        case "text_delta":
          setStreamingContent((prev) => prev + (event.content ?? ""));
          break;

        case "tool_call":
          // Flush streaming content first
          setStreamingContent((prev) => {
            if (prev) {
              setEntries((e) => [...e, makeEntry("assistant", prev)]);
            }
            return "";
          });
          appendEntry(
            makeEntry(
              "tool_call",
              JSON.stringify(event.toolInput ?? {}, null, 2),
              event.toolName
            )
          );
          break;

        case "tool_result":
          appendEntry(
            makeEntry(
              event.isError ? "tool_error" : "tool_result",
              event.toolResult ?? "",
              event.toolName
            )
          );
          break;

        case "error":
          setLoading(false);
          setStreamingContent((prev) => {
            if (prev)
              setEntries((e) => [...e, makeEntry("assistant", prev)]);
            return "";
          });
          appendEntry(makeEntry("error", event.content ?? "Unknown error"));
          break;

        case "done":
          setStreamingContent((prev) => {
            if (prev)
              setEntries((e) => [...e, makeEntry("assistant", prev)]);
            return "";
          });
          setLoading(false);
          break;
      }
    });
  }, [session, appendEntry]);

  // Keyboard: Ctrl+C quit, arrow keys scroll
  useInput((inputChar, key) => {
    if (key.ctrl && inputChar === "c") {
      exit();
      return;
    }
    if (loading) return;
    if (key.upArrow) setScrollOffset((s) => Math.max(0, s - 1));
    if (key.downArrow) setScrollOffset((s) => s + 1);
    if (key.pageUp) setScrollOffset((s) => Math.max(0, s - 10));
    if (key.pageDown) setScrollOffset((s) => s + 10);
  });

  const handleSubmit = useCallback(
    async (value: string) => {
      const text = value.trim();
      if (!text || loading) return;
      setInput("");
      setLoading(true);
      setScrollOffset(0);
      appendEntry(makeEntry("user", text));
      await session.send(text);
    },
    [loading, session, appendEntry]
  );

  // Visible entries: show last N to fit terminal
  const visibleHeight = Math.max((stdout?.rows ?? 40) - 8, 10);
  const allEntries = [
    ...entries,
    ...(streamingContent
      ? [makeEntry("assistant", streamingContent + "▋")]
      : []),
  ];
  const startIdx = Math.max(
    0,
    allEntries.length - visibleHeight - scrollOffset
  );
  const visibleEntries = allEntries.slice(startIdx);

  return (
    <Box flexDirection="column" width={width}>
      {/* Header */}
      <Box
        borderStyle="round"
        borderColor="magenta"
        paddingX={1}
        marginBottom={1}
      >
        <Text color="magenta" bold>
          CodeGen{" "}
        </Text>
        <Text backgroundColor="magenta" color="white">
          {" "}
          {config.llm.provider}{" "}
        </Text>
        <Text> </Text>
        <Text color="gray">{config.llm.model}</Text>
        <Text> </Text>
        {loading && (
          <>
            <Text color="yellow">
              <Spinner type="dots" />
            </Text>
            <Text color="yellow"> processing...</Text>
          </>
        )}
        <Box flexGrow={1} />
        <Text color="gray">{config.workDir}</Text>
      </Box>

      {/* Chat area */}
      <Box flexDirection="column" flexGrow={1}>
        {scrollOffset > 0 && (
          <Text color="gray" italic>
            ↑ {scrollOffset} lines above (↑/↓ to scroll)
          </Text>
        )}
        {visibleEntries.map((entry) => (
          <MessageItem key={entry.id} entry={entry} width={width} />
        ))}
      </Box>

      {/* Input area */}
      <Box
        borderStyle="round"
        borderColor={loading ? "gray" : "green"}
        paddingX={1}
        marginTop={1}
      >
        <Text color={loading ? "gray" : "green"} bold>
          ›{" "}
        </Text>
        {loading ? (
          <Text color="gray" italic>
            (waiting for response...)
          </Text>
        ) : (
          <TextInput
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="Ask me to write, review, or debug code…"
          />
        )}
      </Box>

      {/* Help bar */}
      <Box paddingX={1}>
        <Text color="gray">
          <Text bold color="white">
            Enter
          </Text>
          :send{" "}
          <Text bold color="white">
            ↑↓
          </Text>
          :scroll{" "}
          <Text bold color="white">
            Ctrl+C
          </Text>
          :quit
        </Text>
      </Box>
    </Box>
  );
}
