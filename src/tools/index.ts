import { tool } from "ai";
import { z } from "zod";
import * as fs from "fs/promises";
import * as fsSync from "fs";
import * as path from "path";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

/**
 * Returns the full set of tools available to the LLM.
 * All tools are created with Vercel AI SDK's `tool()` helper which
 * provides automatic Zod schema → JSON Schema conversion and type-safe execution.
 */
export function createTools(workDir: string) {
  return {
    read_file: tool({
      description:
        "Read the contents of a file. Returns content with line numbers.",
      parameters: z.object({
        path: z
          .string()
          .describe("File path (relative to working dir or absolute)"),
        startLine: z
          .number()
          .optional()
          .describe("Start reading from this line (1-indexed)"),
        endLine: z
          .number()
          .optional()
          .describe("Stop reading at this line (inclusive)"),
      }),
      execute: async ({ path: filePath, startLine, endLine }) => {
        const resolved = resolvePath(workDir, filePath);
        try {
          const content = await fs.readFile(resolved, "utf-8");
          const lines = content.split("\n");
          const from = (startLine ?? 1) - 1;
          const to = endLine ?? lines.length;
          return lines
            .slice(from, to)
            .map((l, i) => `${String(from + i + 1).padStart(4)} | ${l}`)
            .join("\n");
        } catch (e) {
          throw new Error(`Failed to read file: ${(e as Error).message}`);
        }
      },
    }),

    write_file: tool({
      description:
        "Write content to a file. Creates directories if needed. Overwrites if exists.",
      parameters: z.object({
        path: z.string().describe("File path relative to working directory"),
        content: z.string().describe("Content to write"),
      }),
      execute: async ({ path: filePath, content }) => {
        const resolved = resolvePath(workDir, filePath);
        await fs.mkdir(path.dirname(resolved), { recursive: true });
        await fs.writeFile(resolved, content, "utf-8");
        return `Written ${content.length} bytes to ${resolved}`;
      },
    }),

    edit_file: tool({
      description:
        "Edit a file by replacing an exact string. old_string must be unique in the file.",
      parameters: z.object({
        path: z.string().describe("File path relative to working directory"),
        oldString: z
          .string()
          .describe("Exact text to replace (must be unique in file)"),
        newString: z.string().describe("Replacement text"),
      }),
      execute: async ({ path: filePath, oldString, newString }) => {
        const resolved = resolvePath(workDir, filePath);
        const content = await fs.readFile(resolved, "utf-8");
        const count = countOccurrences(content, oldString);
        if (count === 0) throw new Error("old_string not found in file");
        if (count > 1)
          throw new Error(
            `old_string appears ${count} times — make it more specific`
          );
        await fs.writeFile(resolved, content.replace(oldString, newString));
        return `Successfully edited ${resolved}`;
      },
    }),

    list_files: tool({
      description: "List files and directories. Use recursive for full tree.",
      parameters: z.object({
        path: z
          .string()
          .optional()
          .describe("Directory to list (default: working dir)"),
        recursive: z
          .boolean()
          .optional()
          .describe("List recursively (default: false)"),
      }),
      execute: async ({ path: dirPath, recursive }) => {
        const resolved = dirPath
          ? resolvePath(workDir, dirPath)
          : workDir;
        if (recursive) {
          return buildTree(resolved, resolved, 0);
        }
        const entries = await fs.readdir(resolved, { withFileTypes: true });
        return entries
          .map((e) => (e.isDirectory() ? `${e.name}/` : e.name))
          .join("\n");
      },
    }),

    bash: tool({
      description:
        "Execute a bash command in the working directory. Avoid interactive commands.",
      parameters: z.object({
        command: z.string().describe("Shell command to run"),
        timeout: z
          .number()
          .optional()
          .describe("Timeout in seconds (default: 30, max: 120)"),
      }),
      execute: async ({ command, timeout = 30 }) => {
        const timeoutMs = Math.min(timeout, 120) * 1000;
        try {
          const { stdout, stderr } = await execAsync(command, {
            cwd: workDir,
            timeout: timeoutMs,
            maxBuffer: 1024 * 1024 * 4, // 4MB
          });
          let result = stdout;
          if (stderr) result += (result ? "\nSTDERR:\n" : "") + stderr;
          return truncate(result || "(no output)", 8000);
        } catch (e: any) {
          const out = [e.stdout, e.stderr].filter(Boolean).join("\nSTDERR:\n");
          return truncate(out || e.message, 8000);
        }
      },
    }),

    search: tool({
      description: "Search for text patterns in files using grep.",
      parameters: z.object({
        pattern: z.string().describe("Search pattern (supports regex)"),
        path: z
          .string()
          .optional()
          .describe("Directory or file to search (default: working dir)"),
        filePattern: z
          .string()
          .optional()
          .describe("Glob to filter files (e.g. '*.ts')"),
        caseInsensitive: z.boolean().optional(),
      }),
      execute: async ({ pattern, path: searchPath, filePattern, caseInsensitive }) => {
        const resolved = searchPath
          ? resolvePath(workDir, searchPath)
          : workDir;
        const args = ["-rn", "--color=never", "-m", "50"];
        if (filePattern) args.push(`--include=${filePattern}`);
        if (caseInsensitive) args.push("-i");
        args.push(pattern, resolved);
        try {
          const { stdout } = await execAsync(`grep ${args.join(" ")}`, {
            timeout: 10000,
          });
          return truncate(stdout || "No matches found", 4000);
        } catch {
          return "No matches found";
        }
      },
    }),
  } as const;
}

export type Tools = ReturnType<typeof createTools>;

// ── Helpers ────────────────────────────────────────────────────────────────

function resolvePath(workDir: string, p: string): string {
  return path.isAbsolute(p) ? p : path.join(workDir, p);
}

function countOccurrences(haystack: string, needle: string): number {
  let count = 0;
  let pos = 0;
  while ((pos = haystack.indexOf(needle, pos)) !== -1) {
    count++;
    pos += needle.length;
  }
  return count;
}

function truncate(s: string, maxLen: number): string {
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen) + `\n...(truncated, ${s.length} total chars)`;
}

async function buildTree(
  baseDir: string,
  dir: string,
  depth: number
): Promise<string> {
  if (depth > 5) return "";
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const lines: string[] = [];
  const indent = "  ".repeat(depth);
  for (const e of entries) {
    if (e.name.startsWith(".") || e.name === "node_modules" || e.name === "dist")
      continue;
    if (e.isDirectory()) {
      lines.push(`${indent}${e.name}/`);
      lines.push(await buildTree(baseDir, path.join(dir, e.name), depth + 1));
    } else {
      lines.push(`${indent}${e.name}`);
    }
  }
  return lines.filter(Boolean).join("\n");
}
