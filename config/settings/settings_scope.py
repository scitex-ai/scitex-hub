"""Optional deployment restrictions over leaf-declared scope capabilities.

App support comes from each installed SDK AppConfig's manifest
``scope_capabilities`` declaration. Overrides may restrict support, never
turn an unsupported operation on. Project ACLs remain provider-owned.
"""

SCITEX_APP_SCOPE_CAPABILITIES = {}
