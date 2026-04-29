# Claude Code Setup & Plugin Configuration

## Overview
This document describes the Claude Code CLI setup, plugin installation, and troubleshooting steps for this environment.

## Installation

Claude Code was installed via the official install script:
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Current Version**: 2.1.96 (native installation)
**Location**: `~/.local/bin/claude`

## Installed Plugins

### All Plugins (13 total)

| Plugin | Version | Marketplace | Status |
|--------|---------|-------------|--------|
| claude-hud | 0.1.0 | claude-hud | ✔ Enabled |
| claude-mem | 12.3.9 | thedotmack | ✔ Enabled |
| code-review | 1.0.0 | claude-code-plugins | ✔ Enabled |
| commit-commands | 1.0.0 | claude-code-plugins | ✔ Enabled |
| equity-research | 0.1.0 | financial-services-plugins | ✔ Enabled |
| financial-analysis | 0.1.0 | financial-services-plugins | ✔ Enabled |
| github | unknown | claude-plugins-official | ✔ Enabled |
| investment-banking | 0.2.0 | financial-services-plugins | ✔ Enabled |
| mcp-apps | 0.1.0 | mcp-apps | ✔ Enabled |
| private-equity | 0.1.0 | financial-services-plugins | ✔ Enabled |
| sales | 1.2.0 | knowledge-work-plugins | ✔ Enabled |
| security-guidance | 1.0.0 | claude-code-plugins | ✔ Enabled |
| warp | 2.0.0 | claude-code-warp | ✔ Enabled |
| wealth-management | 0.1.0 | financial-services-plugins | ✔ Enabled |

### Configured Marketplaces

```bash
claude plugin marketplace list
```

- **claude-plugins-official** - GitHub: anthropics/claude-plugins-official
- **claude-code-warp** - GitHub: warpdotdev/claude-code-warp
- **claude-code-plugins** - GitHub: anthropics/claude-code
- **financial-services-plugins** - GitHub: anthropics/financial-services-plugins
- **anthropic-agent-skills** - GitHub: anthropics/skills
- **claude-hud** - GitHub: jarrodwatts/claude-hud
- **thedotmack** - GitHub: thedotmack/claude-mem
- **knowledge-work-plugins** - GitHub: anthropics/knowledge-work-plugins
- **mcp-apps** - GitHub: modelcontextprotocol/ext-apps

## Troubleshooting

### Fixed: Plugin Schema Validation Errors

**Issue**: Four plugins (equity-research, financial-analysis, private-equity, wealth-management) failed to load with error:
```
Hook load failed: Invalid input: expected object, received array
```

**Root Cause**: The `hooks/hooks.json` files in these plugins contained an empty array `[]` instead of the expected object schema.

**Fix Applied** (2026-04-29):

Updated both marketplace and cache locations:

1. **Marketplace sources**:
   - `~/.claude/plugins/marketplaces/financial-services-plugins/*/hooks/hooks.json`

2. **Cached versions**:
   - `~/.claude/plugins/cache/financial-services-plugins/*/0.1.0/hooks/hooks.json`

Changed from:
```json
[]
```

To:
```json
{
  "hooks": {}
}
```

This matches the schema used by the working `investment-banking` plugin (v0.2.0).

### Health Check Results

```bash
claude doctor
```

**Status**: ✅ Healthy
- Running latest version (2.1.96)
- Auto-updates enabled
- Native installation active

**Warnings Resolved**:
- ✅ Duplicate npm global installation uninstalled
- ⚠️ Large MCP context usage (~414K tokens) - acceptable for current use

## Featured Plugin: Investment Banking

### Commands
- `/one-pager [company]` - One-page strip profile for pitch books
- `/cim [company]` - Draft Confidential Information Memorandum
- `/teaser [company]` - Anonymous one-page company teaser
- `/buyer-list [company]` - Strategic and financial buyer universe
- `/merger-model [deal]` - Accretion/dilution M&A analysis
- `/process-letter [deal]` - Bid instructions and process correspondence
- `/deal-tracker` - Track live deals, milestones, and action items

### Skills
- `cim-builder`, `teaser`, `process-letter`, `buyer-list`, `datapack-builder`
- `strip-profile`, `pitch-deck`
- `merger-model`, `deal-tracker`

### Example Usage
```bash
/one-pager Tesla
/cim Acme Corp
/merger-model Microsoft acquiring Activision
```

## Maintenance

### Update Claude Code
```bash
claude upgrade
```

### Update Plugins
```bash
claude plugin update <plugin-name>
```

### List Plugins
```bash
claude plugin list
```

### Install New Plugin
```bash
# From default marketplace
claude plugin install <plugin-name>

# From specific marketplace
claude plugin install <plugin-name>@<marketplace-name>
```

### Add New Marketplace
```bash
claude plugin marketplace add <owner>/<repo>
```

## MCP Servers

Global MCP servers configured in `~/.claude.json`:
- **pulumi** - Pulumi infrastructure management
- **MCP_DOCKER** - Docker gateway integration
- **openmemory** - Memory persistence (HTTP)
- **composio** - Composio integration (HTTP)

Project-specific MCP servers in `/Users/pranavarora/skills/.warp/.mcp.json`:
- **filesystem** - File system access
- **apple-mcp** - Apple platform integration
- **playwright** - Browser automation

## References

- [Claude Code Documentation](https://docs.anthropic.com/claude/docs)
- [Plugin Development Guide](https://github.com/anthropics/claude-code)
- Installation Date: 2025-02-19
- Last Updated: 2026-04-29

---

Co-Authored-By: Oz <oz-agent@warp.dev>
