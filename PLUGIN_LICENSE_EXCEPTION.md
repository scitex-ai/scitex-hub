# SciTeX Plugin License Exception

Version 1.0, March 2026

## Purpose

SciTeX Cloud is licensed under the GNU Affero General Public License
version 3 (AGPL-3.0). This exception clarifies the licensing status of
third-party apps ("plugins") that use the SciTeX Plugin SDK.

## Exception Statement

As a special exception, the copyright holders of SciTeX Cloud grant you
permission to create apps (workspace modules) that communicate with
SciTeX Cloud solely through the Plugin SDK interfaces listed below,
**without those apps being considered derivative works** of SciTeX Cloud
under the AGPL-3.0.

This means you may license your plugin under any license of your choosing
(MIT, Apache-2.0, BSD, proprietary, etc.) provided the following
conditions are met.

## Conditions

1. **SDK-only interaction.** Your plugin communicates with SciTeX Cloud
   exclusively through the following public interfaces:
   - `ModuleConfig` registration via `workspace_app/registry.py`
   - Context builder functions (`build_*_context(request, current_project)`)
   - AJAX partial templates loaded via the workspace shell
   - Static files served under your app's namespace
   - `manifest.json` metadata schema
   - LLM Skill registration via `llm_app/skills.py`

2. **No core modification.** Your plugin does not modify, monkey-patch,
   or replace any SciTeX Cloud core module, middleware, or template.

3. **Clear attribution.** Your plugin's `manifest.json` includes a valid
   `license` field with an SPDX identifier.

4. **No circumvention.** Your plugin does not bypass security checks,
   authentication, or access controls provided by SciTeX Cloud.

## What This Exception Does NOT Cover

- Modifications to SciTeX Cloud itself (those remain AGPL-3.0)
- Plugins that import or copy substantial portions of SciTeX Cloud source
- Plugins distributed as part of a modified SciTeX Cloud distribution
- The `scitex` Python package (separate license at github.com/ywatanabe1989/scitex)

## Revocation

This exception may be revised in future versions. Plugins created under
a given version of this exception retain that version's terms indefinitely.
