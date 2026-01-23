<!-- ---
!-- Timestamp: 2025-10-15 23:36:35
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/REFACTORING_PLAN_FROM_USER.md
!-- --- -->

no need for orcid, mendely, github, or reference_sync

  also, we no need complecated implementations yet, consider all implementations are just a blueprint

  create future directory to keep code but actually not use them

  most important parts are

1. Landing page
2. Scholar implementation (~/proj/scitex_repo/src/scitex/scholar) has been significantly upgraded
   3. Also, we are planning to create .exe local executable
3. Write implementation (~/proj/neurovista/paper; as an live example)
4. Organized project for scalability and redability (this app itself will be open sourced; but no backward compatibility needed for now)
   5. See this (/home/ywatanabe/proj/scitex-cloud/docs/REFACTORING_PLAN.md) but do not need to completely follow it as our constraint is not strict

<!-- EOF -->