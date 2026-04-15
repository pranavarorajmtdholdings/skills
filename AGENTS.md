# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This repository is a backup/mirror of skills published on [clawdhub.com](https://clawdhub.com). It contains skill definitions that AI coding agents (Claude, Cursor, GPT, Copilot, etc.) can consume.

There is no build system, test suite, or linting — the repo is purely content (Markdown + JSON metadata).

## Repository Structure

Skills live under `skills/<owner>/<slug>/` with three files each:

- `SKILL.md` — The skill definition with YAML frontmatter (name, description, version, keywords) and Markdown body containing instructions, usage examples, and agent instructions.
- `README.md` — Human-readable documentation for the skill.
- `_meta.json` — Publishing metadata: owner, slug, displayName, latest version/commit, and version history.

## Adding or Updating a Skill

1. Create or edit the directory `skills/<owner>/<slug>/`.
2. Ensure all three files (`SKILL.md`, `README.md`, `_meta.json`) are present and consistent.
3. `SKILL.md` frontmatter must include `name`, `description`, `version`, and `keywords`.
4. `_meta.json` must have `owner`, `slug`, `displayName`, and a `latest` object with `version`, `publishedAt` (Unix timestamp in ms), and `commit` URL.

## Conventions

- Skill names use kebab-case (e.g., `ai-pdf-builder`).
- Owner directories match the publisher's handle on clawdhub.com.
- Version strings follow semver (e.g., `1.2.3`).
- The `SKILL.md` body should include an "Agent Instructions" section telling AI agents how to use the skill.

## MCP Configuration

MCP servers can be configured for use alongside this repository:

- **Warp (global):** `~/.warp/.mcp.json` using the `mcpServers` wrapper key. Warp auto-detects changes on save.
- **Warp (project-scoped):** `<repo_root>/.warp/.mcp.json`
- **Claude Code (global):** Configured in `~/.claude.json` under `mcpServers`.
- **Claude Code (project-scoped):** Configured in `~/.claude.json` under `projects.<path>.mcpServers`.

To import MCP servers from Claude Desktop into Claude Code:
```
claude mcp add-from-claude-desktop
```

Servers use either stdio transport (`command` + `args`) or HTTP/SSE transport (`url`). Example stdio config:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@scope/package-name"],
      "env": { "API_KEY": "${API_KEY}" }
    }
  }
}
```

## Plugin Management (Claude Code)

Claude Code plugin commands are slash commands that run inside the Claude Code REPL, not in the shell. Start `claude` first, then:

- `/plugin marketplace add <url>` — Add a plugin marketplace.
- `/plugin install <name>` — Install a plugin.
- `/plugin list` — List installed plugins.
