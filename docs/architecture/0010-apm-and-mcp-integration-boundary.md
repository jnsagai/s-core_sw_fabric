# ADR 0010: APM and MCP integration boundary

Date: 2026-09-27. Status: **Proposed; implement in 007; owner review pending**.

## Decision

Use the selected apm-setup, graphify-codegraph and context-discipline contracts. Setup is explicit and separate from feature runs; pin uvx Git references and actual transport/tool schemas. Cache observations by repository baseline as hints; promote decisions only into reviewed native records.

## Source evidence

[mcp-servers: apm.yml](https://github.com/eclipse-score/mcp-servers/blob/29aeaa8251bd006d7ed3b0ea64229ea8589ce826/apm.yml); [mcp-servers: packages/context-discipline/src/context_discipline_mcp.py](https://github.com/eclipse-score/mcp-servers/blob/29aeaa8251bd006d7ed3b0ea64229ea8589ce826/packages/context-discipline/src/context_discipline_mcp.py); [fabro-nightly: docs/public/agents/mcp.mdx](https://github.com/fabro-sh/fabro/blob/1b4fb15281ebb724426f9e480dce48d0100ff79b/docs/public/agents/mcp.mdx)

## Alternatives considered

APM compilation is not workflow execution. MCP working memory is not evidence authority. The linked metamodel-flow PR artifact is not present in the selected checkout.

## Consequences

Separate external tools used by agents from Fabro lifecycle MCP exposed to coordinators. Mandatory tool-handshake failures must block relevant stages even though Fabro can skip failed MCP servers. Ordinary roles receive no run approval or privileged mutation tools.

## Unresolved assumptions

No actual APM/MCP setup or handshake tested. Graphify language coverage and baseline invalidation must be probed in 007.
