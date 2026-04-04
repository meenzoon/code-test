#!/usr/bin/env node
import { program } from "commander";
import { render } from "ink";
import React from "react";
import chalk from "chalk";
import { loadConfig, saveConfig, getConfigPath } from "./config/config.js";
import { createModel, listModels } from "./providers/index.js";
import { createTools } from "./tools/index.js";
import { Session } from "./session/session.js";
import { App } from "./tui/App.js";

program
  .name("codegen")
  .description(
    "AI-powered code generation CLI — supports Ollama, OpenAI, Anthropic, Groq, Gemini"
  )
  .version("0.1.0")
  .option("-p, --provider <provider>", "LLM provider (ollama|openai|anthropic|groq|gemini)")
  .option("-m, --model <model>", "Model name")
  .option("--base-url <url>", "Custom API base URL")
  .option("--api-key <key>", "API key")
  .option("--no-tools", "Disable tool use")
  .option("--work-dir <dir>", "Working directory")
  .argument("[prompt...]", "One-shot prompt (skips TUI)")
  .action(async (promptArgs: string[], opts) => {
    try {
      const config = loadConfig();

      // Apply CLI flag overrides
      if (opts.provider) config.llm.provider = opts.provider;
      if (opts.model) config.llm.model = opts.model;
      if (opts.baseUrl) config.llm.baseUrl = opts.baseUrl;
      if (opts.apiKey) config.llm.apiKey = opts.apiKey;
      if (opts.workDir) config.workDir = opts.workDir;

      const model = createModel(config.llm);
      const tools = opts.tools ? createTools(config.workDir) : ({} as any);
      const session = new Session({
        model,
        tools,
        systemPrompt: config.systemPrompt,
      });

      // One-shot mode
      if (promptArgs.length > 0) {
        await runOneShot(session, promptArgs.join(" "));
        return;
      }

      // Interactive TUI mode
      const { waitUntilExit } = render(
        React.createElement(App, { config, session }),
        { exitOnCtrlC: false }
      );
      await waitUntilExit();
    } catch (e) {
      console.error(chalk.red("Error:"), (e as Error).message);
      process.exit(1);
    }
  });

// ── Subcommands ────────────────────────────────────────────────────────────

program
  .command("run <prompt...>")
  .description("Run a single prompt (non-interactive)")
  .option("-p, --provider <provider>")
  .option("-m, --model <model>")
  .option("--no-tools")
  .action(async (promptArgs: string[], opts) => {
    const config = loadConfig();
    if (opts.provider) config.llm.provider = opts.provider;
    if (opts.model) config.llm.model = opts.model;

    const model = createModel(config.llm);
    const tools = opts.tools ? createTools(config.workDir) : ({} as any);
    const session = new Session({ model, tools, systemPrompt: config.systemPrompt });
    await runOneShot(session, promptArgs.join(" "));
  });

program
  .command("models")
  .description("List available models for the current provider")
  .option("-p, --provider <provider>")
  .action(async (opts) => {
    const config = loadConfig();
    if (opts.provider) config.llm.provider = opts.provider;
    try {
      const models = await listModels(config.llm.provider, config.llm);
      console.log(chalk.bold(`Models for ${chalk.magenta(config.llm.provider)}:`));
      models.forEach((m) => console.log(`  ${chalk.cyan("•")} ${m}`));
    } catch (e) {
      console.error(chalk.red("Failed to list models:"), (e as Error).message);
    }
  });

program
  .command("config")
  .description("Show or update configuration")
  .option("--set-provider <provider>")
  .option("--set-model <model>")
  .option("--set-api-key <key>")
  .action((opts) => {
    const config = loadConfig();

    if (opts.setProvider || opts.setModel || opts.setApiKey) {
      if (opts.setProvider) config.llm.provider = opts.setProvider;
      if (opts.setModel) config.llm.model = opts.setModel;
      if (opts.setApiKey) config.llm.apiKey = opts.setApiKey;
      saveConfig(config);
      console.log(chalk.green("✓ Config saved"));
    }

    console.log(chalk.bold("Current configuration:"));
    console.log(`  Provider:    ${chalk.cyan(config.llm.provider)}`);
    console.log(`  Model:       ${chalk.cyan(config.llm.model)}`);
    console.log(`  Base URL:    ${config.llm.baseUrl || chalk.gray("(default)")}`);
    console.log(`  Max Tokens:  ${config.llm.maxTokens}`);
    console.log(`  Temperature: ${config.llm.temperature}`);
    console.log(`  Work Dir:    ${config.workDir}`);
    console.log(`  Config file: ${chalk.gray(getConfigPath())}`);

    const key = config.llm.apiKey;
    if (key) {
      const masked =
        key.length > 8 ? `${key.slice(0, 4)}...${key.slice(-4)}` : "****";
      console.log(`  API Key:     ${chalk.gray(masked)}`);
    }
  });

program.parse();

// ── One-shot helper ────────────────────────────────────────────────────────

async function runOneShot(session: Session, prompt: string): Promise<void> {
  session.setEventHandler((event) => {
    switch (event.type) {
      case "text_delta":
        process.stdout.write(event.content ?? "");
        break;
      case "tool_call":
        process.stderr.write(
          chalk.yellow(`\n[Tool: ${event.toolName}]\n`)
        );
        break;
      case "tool_result":
        process.stderr.write(
          chalk.cyan(
            `[Result: ${event.toolName}] ${truncate(event.toolResult ?? "", 200)}\n`
          )
        );
        break;
      case "error":
        process.stderr.write(chalk.red(`\nError: ${event.content}\n`));
        break;
      case "done":
        process.stdout.write("\n");
        break;
    }
  });
  await session.send(prompt);
}

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n) + "...";
}
