import React from "react";
import { Box, Text } from "ink";
import type { ChatEntry } from "./types.js";

interface Props {
  entry: ChatEntry;
  width: number;
}

export function MessageItem({ entry, width }: Props) {
  switch (entry.kind) {
    case "user":
      return (
        <Box flexDirection="column" marginBottom={1}>
          <Text color="green" bold>
            You
          </Text>
          <Box marginLeft={1}>
            <Text wrap="wrap">{entry.content}</Text>
          </Box>
          <Text color="gray">{separator(Math.min(width - 2, 60))}</Text>
        </Box>
      );

    case "assistant":
      return (
        <Box flexDirection="column" marginBottom={1}>
          <Text color="magenta" bold>
            Assistant
          </Text>
          <MarkdownText text={entry.content} />
          <Text color="gray">{separator(Math.min(width - 2, 60))}</Text>
        </Box>
      );

    case "tool_call":
      return (
        <Box flexDirection="column" marginLeft={1} marginBottom={0}>
          <Text color="yellow" bold>
            ⚙ Tool: {entry.meta}
          </Text>
          <Box borderStyle="single" borderColor="yellow" paddingX={1}>
            <Text color="gray" wrap="wrap">
              {truncate(entry.content, 300)}
            </Text>
          </Box>
        </Box>
      );

    case "tool_result":
      return (
        <Box flexDirection="column" marginLeft={1} marginBottom={1}>
          <Text color="cyan" bold>
            ✓ Result: {entry.meta}
          </Text>
          <Box borderStyle="single" borderColor="cyan" paddingX={1}>
            <Text color="gray" wrap="wrap">
              {truncate(entry.content, 400)}
            </Text>
          </Box>
        </Box>
      );

    case "tool_error":
      return (
        <Box flexDirection="column" marginLeft={1} marginBottom={1}>
          <Text color="red" bold>
            ✗ Error: {entry.meta}
          </Text>
          <Box borderStyle="single" borderColor="red" paddingX={1}>
            <Text color="red" wrap="wrap">
              {truncate(entry.content, 300)}
            </Text>
          </Box>
        </Box>
      );

    case "error":
      return (
        <Box marginBottom={1}>
          <Text color="red" bold>
            Error:{" "}
          </Text>
          <Text color="red" wrap="wrap">
            {entry.content}
          </Text>
        </Box>
      );

    case "info":
      return (
        <Box marginBottom={1}>
          <Text color="gray" italic>
            {entry.content}
          </Text>
        </Box>
      );
  }
}

/** Basic markdown rendering: code blocks, bold, inline code */
function MarkdownText({ text }: { text: string }) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let inCode = false;
  let codeLang = "";
  let codeLines: string[] = [];
  let key = 0;

  for (const line of lines) {
    if (line.startsWith("```")) {
      if (!inCode) {
        inCode = true;
        codeLang = line.slice(3).trim();
        codeLines = [];
      } else {
        inCode = false;
        elements.push(
          <Box
            key={key++}
            flexDirection="column"
            borderStyle="round"
            borderColor="gray"
            paddingX={1}
            marginLeft={2}
            marginBottom={1}
          >
            {codeLang && (
              <Text color="gray" italic>
                {codeLang}
              </Text>
            )}
            <Text color="blueBright">{codeLines.join("\n")}</Text>
          </Box>
        );
        codeLang = "";
      }
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      continue;
    }

    elements.push(
      <Box key={key++} marginLeft={1}>
        <InlineLine text={line} />
      </Box>
    );
  }

  // Unclosed code block
  if (inCode && codeLines.length > 0) {
    elements.push(
      <Box key={key++} marginLeft={2} borderStyle="round" borderColor="gray" paddingX={1}>
        <Text color="blueBright">{codeLines.join("\n")}</Text>
      </Box>
    );
  }

  return <Box flexDirection="column">{elements}</Box>;
}

/** Render a single line with inline formatting (bold, inline code) */
function InlineLine({ text }: { text: string }) {
  // Simple pass-through; full inline markdown parser is complex for a TUI
  // Handle **bold** and `code` visually
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Inline code
    const codeMatch = remaining.match(/`([^`]+)`/);

    const boldIdx = boldMatch?.index ?? Infinity;
    const codeIdx = codeMatch?.index ?? Infinity;

    if (boldIdx === Infinity && codeIdx === Infinity) {
      parts.push(<Text key={key++}>{remaining}</Text>);
      break;
    }

    if (boldIdx <= codeIdx && boldMatch) {
      if (boldIdx > 0) parts.push(<Text key={key++}>{remaining.slice(0, boldIdx)}</Text>);
      parts.push(<Text key={key++} bold>{boldMatch[1]}</Text>);
      remaining = remaining.slice(boldIdx + boldMatch[0].length);
    } else if (codeMatch) {
      if (codeIdx > 0) parts.push(<Text key={key++}>{remaining.slice(0, codeIdx)}</Text>);
      parts.push(<Text key={key++} color="blueBright" backgroundColor="gray">{` ${codeMatch[1]} `}</Text>);
      remaining = remaining.slice(codeIdx + codeMatch[0].length);
    }
  }

  return <Text wrap="wrap">{parts}</Text>;
}

function separator(len: number): string {
  return "─".repeat(Math.max(len, 0));
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n) + "…(truncated)";
}
