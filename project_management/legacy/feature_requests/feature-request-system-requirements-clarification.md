# Feature Request: Clarify System Requirements for SciTeX Components

**Date**: 2025-05-23
**Priority**: High
**Category**: Documentation & Infrastructure

## Summary

Clarify and document the system requirements for each SciTeX component, particularly addressing:
- SciTeX-Engine's dependency on Claude Code
- SciTeX-Viz's dependency on Windows and VisPlot
- Linux compatibility and Apptainer containerization strategy

## Current Situation

The SciTeX ecosystem components have varying system requirements that are not clearly documented:
- Some components require specific proprietary software
- Platform dependencies (Windows vs Linux) are unclear
- Containerization strategy needs definition

## Proposed Changes

### 1. Document Component Requirements

Create clear documentation for each component's dependencies:

#### SciTeX-Engine
- **Requires**: Claude Code (Anthropic's CLI tool)
- **Platform**: Linux/macOS/Windows
- **Integration**: Emacs environment
- **Container Strategy**: Package Claude Code within Apptainer if needed

#### SciTeX-Viz
- **Requires**: Windows OS + VisPlot (proprietary software)
- **Current Platform**: Windows only
- **Container Strategy**: 
  - Option A: Wine/Windows compatibility layer in Apptainer
  - Option B: Remote Windows server for VisPlot processing
  - Option C: Develop Linux-native alternative visualization backend

#### Other Components
- **SciTeX-Doc**: Pure LaTeX, Linux-native
- **SciTeX-Code**: Python-based, Linux-native
- **SciTeX-Search**: Web-based, Linux-native
- **SciTeX-Cloud**: Django-based, Linux-native

### 2. Containerization Strategy

Implement Apptainer containers for:
- Components with complex dependencies
- Windows-based components (using compatibility layers)
- Ensuring reproducible environments

### 3. Update Product Pages

Modify product description pages to clearly state:
- System requirements
- Dependencies (open source vs proprietary)
- Container availability
- Platform compatibility

### 4. Infrastructure Considerations

- Set up Apptainer registry for container distribution
- Document container usage instructions
- Provide fallback options for users without container support

## Implementation Steps

1. Create `docs/SYSTEM_REQUIREMENTS.md` with detailed requirements
2. Update all product pages with requirement badges/notices
3. Develop Apptainer definitions for each component
4. Test containerized versions on various Linux distributions
5. Create user guides for container deployment

## Benefits

- Clear expectations for users
- Simplified deployment through containers
- Better support for Linux-only environments
- Reduced support burden

## Technical Considerations

- Licensing implications for containerizing proprietary software
- Performance overhead of compatibility layers
- Network requirements for remote processing options

## Alternative Solutions

For SciTeX-Viz specifically:
1. Develop open-source alternatives to VisPlot functionality
2. Create API bridge to cloud-hosted Windows instances
3. Partner with VisPlot for Linux version or container license

## Success Criteria

- All components can run in Linux environment (native or containerized)
- Clear documentation of requirements and limitations
- User feedback confirms ease of deployment
- Reduced dependency-related support tickets
