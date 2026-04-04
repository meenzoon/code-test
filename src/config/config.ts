import Conf from "conf";
import { z } from "zod";
import * as path from "path";
import * as os from "os";

export const ProviderSchema = z.enum([
  "ollama",
  "openai",
  "anthropic",
  "groq",
  "gemini",
]);
export type Provider = z.infer<typeof ProviderSchema>;

export const DEFAULT_SYSTEM_PROMPT = `You are an expert software engineer and coding assistant.
You help users write, review, debug, and refactor code.
When writing code, always provide complete, working implementations.
When editing files, use the provided tools to read and modify files directly.
Be concise and focus on the task at hand.`;

export const LLMConfigSchema = z.object({
  provider: ProviderSchema.default("ollama"),
  model: z.string().default("llama3.2"),
  baseUrl: z.string().optional(),
  apiKey: z.string().optional(),
  maxTokens: z.number().default(4096),
  temperature: z.number().default(0.7),
});
export type LLMConfig = z.infer<typeof LLMConfigSchema>;

export const ConfigSchema = z.object({
  llm: LLMConfigSchema,
  workDir: z.string().default(process.cwd()),
  theme: z.enum(["dark", "light"]).default("dark"),
  systemPrompt: z.string().default(DEFAULT_SYSTEM_PROMPT),
});
export type Config = z.infer<typeof ConfigSchema>;

const store = new Conf<Partial<Config>>({
  projectName: "codegen",
  schema: {
    llm: { type: "object" },
    workDir: { type: "string" },
    theme: { type: "string", enum: ["dark", "light"] },
    systemPrompt: { type: "string" },
  } as any,
});

export function loadConfig(): Config {
  const stored = store.store;

  // Merge env vars
  const apiKeys: Partial<Record<Provider, string>> = {
    openai: process.env.OPENAI_API_KEY,
    anthropic: process.env.ANTHROPIC_API_KEY,
    groq: process.env.GROQ_API_KEY,
    gemini: process.env.GEMINI_API_KEY,
  } as any;

  const provider = (process.env.CODEGEN_PROVIDER ||
    stored.llm?.provider ||
    "ollama") as Provider;

  const llm: LLMConfig = {
    provider,
    model: process.env.CODEGEN_MODEL || stored.llm?.model || getDefaultModel(provider),
    baseUrl: process.env.CODEGEN_BASE_URL || stored.llm?.baseUrl,
    apiKey: process.env.CODEGEN_API_KEY || stored.llm?.apiKey || apiKeys[provider],
    maxTokens: stored.llm?.maxTokens ?? 4096,
    temperature: stored.llm?.temperature ?? 0.7,
  };

  return ConfigSchema.parse({
    llm,
    workDir: stored.workDir || process.cwd(),
    theme: stored.theme || "dark",
    systemPrompt: stored.systemPrompt || DEFAULT_SYSTEM_PROMPT,
  });
}

export function saveConfig(config: Partial<Config>): void {
  if (config.llm) store.set("llm", config.llm);
  if (config.workDir) store.set("workDir", config.workDir);
  if (config.theme) store.set("theme", config.theme);
  if (config.systemPrompt) store.set("systemPrompt", config.systemPrompt);
}

export function getConfigPath(): string {
  return path.join(os.homedir(), ".config", "codegen", "config.json");
}

function getDefaultModel(provider: Provider): string {
  const defaults: Record<Provider, string> = {
    ollama: "llama3.2",
    openai: "gpt-4o",
    anthropic: "claude-sonnet-4-6",
    groq: "llama-3.3-70b-versatile",
    gemini: "gemini-2.0-flash",
  };
  return defaults[provider];
}
