import { createOpenAI } from "@ai-sdk/openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createGroq } from "@ai-sdk/groq";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import type { LanguageModelV1 } from "ai";
import type { LLMConfig, Provider } from "../config/config.js";

/**
 * Creates a Vercel AI SDK LanguageModelV1 from our config.
 * All providers share the same streaming/tool-call interface via the AI SDK.
 * Ollama uses the OpenAI-compatible endpoint (supported natively by @ai-sdk/openai).
 */
export function createModel(cfg: LLMConfig): LanguageModelV1 {
  switch (cfg.provider) {
    case "ollama": {
      // Ollama exposes an OpenAI-compatible API at /v1
      const ollama = createOpenAI({
        baseURL: (cfg.baseUrl || "http://localhost:11434") + "/v1",
        apiKey: "ollama", // required by SDK but ignored by Ollama
      });
      return ollama(cfg.model);
    }

    case "openai": {
      const openai = createOpenAI({
        baseURL: cfg.baseUrl,
        apiKey: cfg.apiKey || process.env.OPENAI_API_KEY || "",
      });
      return openai(cfg.model);
    }

    case "anthropic": {
      const anthropic = createAnthropic({
        baseURL: cfg.baseUrl,
        apiKey: cfg.apiKey || process.env.ANTHROPIC_API_KEY || "",
      });
      return anthropic(cfg.model);
    }

    case "groq": {
      const groq = createGroq({
        apiKey: cfg.apiKey || process.env.GROQ_API_KEY || "",
      });
      return groq(cfg.model);
    }

    case "gemini": {
      const google = createGoogleGenerativeAI({
        apiKey: cfg.apiKey || process.env.GEMINI_API_KEY || "",
      });
      return google(cfg.model);
    }

    default:
      throw new Error(`Unknown provider: ${cfg.provider}`);
  }
}

/** List models for a given provider */
export async function listModels(
  provider: Provider,
  cfg: LLMConfig
): Promise<string[]> {
  switch (provider) {
    case "ollama": {
      const res = await fetch(
        `${cfg.baseUrl || "http://localhost:11434"}/api/tags`
      );
      if (!res.ok) throw new Error(`Ollama error: ${res.statusText}`);
      const data = (await res.json()) as { models: { name: string }[] };
      return data.models.map((m) => m.name);
    }

    case "openai": {
      const baseURL = cfg.baseUrl || "https://api.openai.com/v1";
      const res = await fetch(`${baseURL}/models`, {
        headers: { Authorization: `Bearer ${cfg.apiKey}` },
      });
      if (!res.ok) throw new Error(`OpenAI error: ${res.statusText}`);
      const data = (await res.json()) as { data: { id: string }[] };
      return data.data.map((m) => m.id).sort();
    }

    case "anthropic":
      return [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
      ];

    case "groq":
      return [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
      ];

    case "gemini":
      return [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
      ];

    default:
      return [];
  }
}
