Valid DetectifAI MCP config, per client (key must never be pasted literally into JSON):

**Cursor / generic JSON clients** (~/.cursor/mcp.json):
```json
{
  "mcpServers": {
    "detectif": {
      "url": "https://platform.detectif.ai/mcp",
      "headers": { "Authorization": "Bearer ${env:DETECTIF_API_KEY}" }
    }
  }
}
```

**Codex** (~/.codex/config.toml, TOML — already wired for you):
```toml
[mcp_servers.detectif]
url = "https://platform.detectif.ai/mcp"
bearer_token_env_var = "DETECTIF_API_KEY"
```

**Claude Code** (CLI):
```bash
claude mcp add --transport http detectif https://platform.detectif.ai/mcp \
  --header "Authorization: Bearer $DETECTIF_API_KEY"
```
