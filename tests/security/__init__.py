# Security regression suite.
#
# Every confirmed security finding gets a test here that REPRODUCES the
# exploit and asserts it is BLOCKED. A gate that cannot fail is not a gate:
# each test in this package must fail when the corresponding fix is reverted.
