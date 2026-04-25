"""A2A protocol app — fleet-wide agent capability surface.

Serves Google A2A AgentCard discovery + JSON-RPC task dispatch at
the dedicated subdomain ``a2a.scitex.ai`` (mirrors the ``git.scitex.ai``
identity-host pattern).

Routes:
  GET  /.well-known/agent.json              fleet-level AgentCard
  GET  /v1/agents/                          fleet roster
  GET  /v1/agents/<name>/.well-known/agent.json  per-agent AgentCard
  POST /v1/agents/<name>                    JSON-RPC tasks/send, tasks/get

Reply implementation today: canned echo. Bridging A2A tasks to live
Channels-driven agents (the orochi runtime on mba) is Tier 3 work —
this NAS-side app reverse-proxies dispatch later via internal route.
"""
