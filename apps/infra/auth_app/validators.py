"""Username validation for SciTeX Cloud"""


def get_reserved_usernames():
    """
    Get dynamically generated list of reserved usernames.
    Syncs with RESERVED_PATHS from config.urls
    """
    try:
        from config.urls import RESERVED_PATHS

        # Remove file extensions and convert to set
        reserved = set()
        for path in RESERVED_PATHS:
            # Remove extensions like .ico, .txt, .xml
            path_clean = path.split(".")[0]
            reserved.add(path_clean)

        # Add guest prefix (for guest sessions)
        reserved.add("guest")

        return reserved
    except ImportError:
        # Fallback if import fails
        return {
            "admin",
            "api",
            "auth",
            "billing",
            "cloud",
            "code",
            "core",
            "dev",
            "docs",
            "integrations",
            "project",
            "scholar",
            "viz",
            "writer",
            "new",
            "static",
            "media",
            "guest",
            "about",
            "help",
            "support",
            "contact",
            "terms",
            "privacy",
            "settings",
            "dashboard",
            "profile",
            "account",
            "login",
            "logout",
            "signup",
            "register",
            "reset",
            "verify",
            "confirm",
        }


def is_username_reserved(username):
    """
    Check if username is reserved and cannot be used.

    Args:
        username: Username to check

    Returns:
        bool: True if reserved, False if available
    """
    if not username:
        return True

    username_lower = username.lower()
    reserved_usernames = get_reserved_usernames()

    # Check exact match
    if username_lower in reserved_usernames:
        return True

    # Check if starts with guest- (reserved for guest sessions)
    if username_lower.startswith("guest-"):
        return True

    # Check if starts with any reserved prefix followed by dash or number
    for reserved in reserved_usernames:
        if username_lower.startswith(f"{reserved}-") or username_lower.startswith(
            f"{reserved}_"
        ):
            return True

    return False


def validate_username(username):
    """
    Validate username meets requirements.

    Args:
        username: Username to validate

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not username:
        return False, "Username is required"

    # Length check
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 30:
        return False, "Username must be at most 30 characters long"

    # Character check (alphanumeric, dash, underscore only)
    import re

    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return (
            False,
            "Username can only contain letters, numbers, dashes, and underscores",
        )

    # Cannot start or end with dash/underscore
    if username[0] in "-_" or username[-1] in "-_":
        return False, "Username cannot start or end with dash or underscore"

    # Reserved check
    if is_username_reserved(username):
        return False, f"Username '{username}' is reserved and cannot be used"

    return True, None
