#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is this login's email address VERIFIED by the provider?

The whole account-linking design rests on one sentence: the same verified
email address always means the same human. That is only safe if "verified"
is something the provider actually asserted — an address a provider merely
ECHOED BACK is an attacker-supplied string, and treating it as an account key
is account takeover.

So this module answers in a fixed, three-valued shape and never a bare bool.
"Cannot tell" is its own state, because collapsing unknown into either pole
is how this class of bug ships: collapse it into "verified" and you hand out
accounts; collapse it into "unverified" silently and you cannot tell a
provider that omits the claim from one that denies it.

PURE — no Django, no database, no network. Takes an allauth ``SocialLogin``
(or anything with the same two attributes) and returns a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The three verdict states. ``verified`` is the ONLY one that may key an
#: account — see :meth:`EmailVerdict.is_account_key`.
VERIFIED = "verified"
UNVERIFIED = "unverified"
UNKNOWN = "unknown"

VALID_STATUSES: tuple[str, ...] = (VERIFIED, UNVERIFIED, UNKNOWN)


class EmailVerdictError(ValueError):
    """Raised when a verdict is constructed in a self-contradictory shape.

    Validates at the point of construction rather than three layers
    downstream, per the SciTeX fixed-shape convention.
    """


@dataclass(frozen=True)
class EmailVerdict:
    """What we know about this login's email address.

    Attributes
    ----------
    email : str | None
        The normalised (stripped, lowercased) address, or ``None`` when the
        login carried none at all.
    status : str
        One of :data:`VALID_STATUSES`. ``verified`` means the provider
        asserted it; ``unverified`` means the provider supplied an address
        and did NOT assert it; ``unknown`` means the login carried no
        address, or carried one whose verification state we could not read.
    source : str
        Where the verdict came from, for logs and for debugging a provider
        that changes its payload shape. Free text, never parsed.
    """

    email: str | None
    status: str
    source: str

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise EmailVerdictError(
                f"invalid status {self.status!r}; must be one of "
                f"{VALID_STATUSES}"
            )
        if self.status == VERIFIED and not self.email:
            raise EmailVerdictError(
                "a 'verified' verdict must carry an email address; got "
                f"email={self.email!r} (this shape would let an empty "
                "address key an account)"
            )

    @property
    def is_account_key(self) -> bool:
        """Whether this address may be used to identify/link an account.

        True for ``verified`` ONLY. Both other states are fail-closed: an
        unverified address is attacker-controllable, and an unknown one is
        exactly the case we refuse to guess about.
        """
        return self.status == VERIFIED


def normalize_email(raw: object) -> str | None:
    """Lowercase + strip an address, or ``None`` when it is not usable.

    Case-folding is what makes the uniqueness constraint mean what people
    assume it means: without it ``Alice@x.com`` and ``alice@x.com`` are two
    account keys for one mailbox. Deliberately does NOT validate the address
    shape — Django's ``EmailField`` does that at the storage boundary, and
    duplicating the rule here would give us two definitions to keep in sync.
    """
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().lower()
    return cleaned or None


def _verdict_from_email_addresses(addresses) -> "EmailVerdict | None":
    """Read allauth's parsed ``EmailAddress`` list; ``None`` if it says nothing.

    This is the PRIMARY source and it is provider-agnostic on purpose: each
    allauth provider implements ``extract_email_addresses`` and sets
    ``verified`` from whatever claim its own API uses (Google's
    ``email_verified``, etc). Reading the parsed result means a new provider
    is handled correctly without a change here.

    A verified address wins over an unverified one regardless of order, so a
    provider that lists a primary-but-unverified address ahead of a verified
    one cannot downgrade the verdict.
    """
    if not addresses:
        return None
    fallback: EmailVerdict | None = None
    for address in addresses:
        email = normalize_email(getattr(address, "email", None))
        if email is None:
            continue
        if getattr(address, "verified", False):
            return EmailVerdict(
                email=email,
                status=VERIFIED,
                source="sociallogin.email_addresses",
            )
        if fallback is None:
            fallback = EmailVerdict(
                email=email,
                status=UNVERIFIED,
                source="sociallogin.email_addresses",
            )
    return fallback


def _verdict_from_extra_data(extra_data) -> "EmailVerdict | None":
    """Fall back to the RAW provider payload; ``None`` if it says nothing.

    Reached only when allauth parsed no address at all — e.g. a provider
    whose ``extract_email_addresses`` returns nothing but whose payload
    still carries the standard OIDC ``email`` / ``email_verified`` claims.

    This is a second READER of the same fact, not a second POLICY: an
    address here is still only ``verified`` when the payload explicitly says
    so. A payload with an address and no verification claim yields
    ``unverified``, never ``unknown`` — the provider did supply an address,
    it just did not vouch for it, and those are different states.
    """
    if not isinstance(extra_data, dict):
        return None
    email = normalize_email(extra_data.get("email"))
    if email is None:
        return None
    # Providers spell this claim differently and type it inconsistently —
    # OIDC says boolean ``email_verified``, some APIs send the string
    # "true", Google's older userinfo used ``verified_email``. Anything not
    # explicitly affirmative is NOT an assertion.
    raw_claim = extra_data.get("email_verified", extra_data.get("verified_email"))
    affirmative = raw_claim is True or (
        isinstance(raw_claim, str) and raw_claim.strip().lower() == "true"
    )
    return EmailVerdict(
        email=email,
        status=VERIFIED if affirmative else UNVERIFIED,
        source="sociallogin.account.extra_data",
    )


def verified_email_of(sociallogin) -> EmailVerdict:
    """Verdict for an allauth ``SocialLogin``.

    Reads allauth's parsed ``email_addresses`` first, then the raw
    ``account.extra_data`` payload, and returns ``unknown`` when neither
    carries an address. Never raises on a malformed login — a login we
    cannot read is exactly an ``unknown``, and the caller fails closed on it.

    Parameters
    ----------
    sociallogin
        An allauth ``SocialLogin``, or any object exposing
        ``email_addresses`` and ``account.extra_data``.

    Returns
    -------
    EmailVerdict
        Always a verdict; check :attr:`EmailVerdict.is_account_key` before
        using the address for anything identity-bearing.
    """
    verdict = _verdict_from_email_addresses(
        getattr(sociallogin, "email_addresses", None)
    )
    if verdict is not None:
        return verdict

    account = getattr(sociallogin, "account", None)
    verdict = _verdict_from_extra_data(getattr(account, "extra_data", None))
    if verdict is not None:
        return verdict

    return EmailVerdict(email=None, status=UNKNOWN, source="no-email-in-login")


__all__ = [
    "UNKNOWN",
    "UNVERIFIED",
    "VALID_STATUSES",
    "VERIFIED",
    "EmailVerdict",
    "EmailVerdictError",
    "normalize_email",
    "verified_email_of",
]

# EOF
