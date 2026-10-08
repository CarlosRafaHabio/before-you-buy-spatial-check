"""H15 -- strict signed synthetic approval checked by a PUBLIC key.

ONLY trusted host code provisions public key mapping, expected context,
UTC clock and the durable ledger. This experimental module has no signing
key and issues no human approval. cryptography is a TEST-ONLY dependency.

A cryptographic signature proves assertion integrity relative to a key.
It DOES NOT prove real human consent, secure issuer identity, guest caller
identity, provider idempotency, or secure handling of host secret keys.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .durable_claim_v0 import (
    DurableClaimV0, GrantScope, dispatch_synthetic_once,
)

_AUDIENCE = "spatial-check.h15.synthetic-broker"
_OPERATION = "directory.lookup_user"
_FIELDS = frozenset({
    "v", "key_id", "grant_id", "epoch", "user_id", "operation",
    "audience", "context_sha256", "actor_claim", "issued_at", "expires_at",
})
_KEY_ID = re.compile(r"ISS-[0-9]{4}\Z", re.ASCII)
_ACTOR = re.compile(r"ACTOR-[0-9]{4}\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_MAX_TOKEN_SIZE = 1024
_MAX_LIFETIME_SECS = 300


@dataclass(frozen=True, slots=True)
class SignedApproval:
    payload: bytes
    signature: bytes


@dataclass(frozen=True, slots=True)
class Verification:
    code: str
    scope: GrantScope | None = None
    asserted_actor: str | None = None
    payload_digest: str | None = None


def canonical_payload(fields: dict[str, object]) -> bytes:
    """For trusted signing test-fixture only; NEVER interprets guest code."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _no_duplicate_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, val in pairs:
        if key in obj:
            raise ValueError("Duplicate approval claim field.")
        obj[key] = val
    return obj


class PublicApprovalVerifier:
    """Immutable snapshot of trusted ISS-ID to raw 32-byte public keys.

    The trusted host chooses which keys to trust. Do not supply this mapping
    from a Monty guest or an untrusted review document.
    """
    __slots__ = ("_keys",)

    def __init__(self, public_keys: Mapping[str, bytes]):
        if not isinstance(public_keys, Mapping) or not public_keys:
            raise ValueError("Trusted issuer public keys required.")
        keys: dict[str, bytes] = {}
        for key_id, raw in public_keys.items():
            if (type(key_id) is not str or _KEY_ID.fullmatch(key_id) is None
                    or type(raw) is not bytes or len(raw) != 32):
                raise ValueError("Malformed trusted issuer public key.")
            keys[key_id] = raw
        self._keys = MappingProxyType(keys.copy())

    def verify(self, signed: object, *, expected_context_sha256: str,
               now_utc: int) -> Verification:
        if (type(expected_context_sha256) is not str
                or _SHA.fullmatch(expected_context_sha256) is None
                or type(now_utc) is not int):
            return Verification("DENY_HOST_VERIFIER_CONFIG")
        if (type(signed) is not SignedApproval
                or type(signed.payload) is not bytes
                or type(signed.signature) is not bytes
                or not 1 <= len(signed.payload) <= _MAX_TOKEN_SIZE
                or len(signed.signature) != 64):
            return Verification("DENY_MALFORMED_APPROVAL")
        try:
            fields = json.loads(
                signed.payload.decode("ascii"),
                object_pairs_hook=_no_duplicate_fields,
            )
            if (type(fields) is not dict or set(fields) != _FIELDS
                    or canonical_payload(fields) != signed.payload):
                return Verification("DENY_MALFORMED_APPROVAL")
        except (ValueError, UnicodeError, TypeError, OverflowError):
            return Verification("DENY_MALFORMED_APPROVAL")

        # Only parse/lookup the issuer key ID before verifying signed bytes.
        # Every other claim must be evaluated AFTER verification, so an
        # attacker changing a previously signed operation/audience/user
        # cannot make the verifier treat unverified text as scope evidence.
        if (type(fields["key_id"]) is not str
                or _KEY_ID.fullmatch(fields["key_id"]) is None):
            return Verification("DENY_MALFORMED_APPROVAL")
        key_bytes = self._keys.get(fields["key_id"])
        if key_bytes is None:
            return Verification("DENY_UNKNOWN_ISSUER")
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signed.signature, signed.payload
            )
        except InvalidSignature:
            return Verification("DENY_INVALID_SIGNATURE")
        except (ValueError, TypeError):
            return Verification("DENY_MALFORMED_APPROVAL")

        # After signature verification, the trusted issuer's FULL signed
        # assertions can be checked for the fixed host policy.
        if (type(fields["v"]) is not int or fields["v"] != 1
                or type(fields["operation"]) is not str
                or fields["operation"] != _OPERATION
                or type(fields["audience"]) is not str
                or fields["audience"] != _AUDIENCE
                or type(fields["context_sha256"]) is not str
                or _SHA.fullmatch(fields["context_sha256"]) is None
                or type(fields["actor_claim"]) is not str
                or _ACTOR.fullmatch(fields["actor_claim"]) is None
                or type(fields["issued_at"]) is not int
                or type(fields["expires_at"]) is not int):
            return Verification("DENY_APPROVAL_SCOPE")
        if fields["context_sha256"] != expected_context_sha256:
            return Verification("DENY_CONTEXT_MISMATCH")
        if (fields["issued_at"] > now_utc
                or fields["expires_at"] <= now_utc
                or not 0 < fields["expires_at"] - fields["issued_at"]
                <= _MAX_LIFETIME_SECS):
            return Verification("DENY_APPROVAL_EXPIRED_OR_NOT_YET_VALID")
        try:
            scope = GrantScope(
                fields["grant_id"], fields["epoch"], fields["user_id"]
            )
        except ValueError:
            return Verification("DENY_APPROVAL_SCOPE")
        return Verification(
            "VERIFIED_ISSUER_SIGNATURE",
            scope,
            fields["actor_claim"],
            sha256(signed.payload).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class AuthorizedDispatch:
    code: str
    attempted: bool = False
    state: str | None = None


def dispatch_with_signed_approval(
    *, verifier: PublicApprovalVerifier, signed: SignedApproval,
    expected_context_sha256: str, now_utc: int,
    ledger: DurableClaimV0, raw_user_id: object,
    trusted_broker_mode: str, scratch_log: Path,
    timeout_secs: float = 1.0,
) -> AuthorizedDispatch:
    """A new, restricted host path, NOT a replacement for all H14 paths.

    Neither agent nor untrusted document may choose expected context, key
    mapping, now_utc, broker mode, scratch path or ledger object.
    """
    if type(verifier) is not PublicApprovalVerifier:
        return AuthorizedDispatch("DENY_VERIFIER_UNAVAILABLE")
    v = verifier.verify(
        signed, expected_context_sha256=expected_context_sha256,
        now_utc=now_utc,
    )
    if v.scope is None:
        return AuthorizedDispatch(v.code)
    if type(ledger) is not DurableClaimV0:
        return AuthorizedDispatch("DENY_LEDGER_UNAVAILABLE")
    # No grant is created on bad signature, wrong audience, expired/changed
    # context, and the worker is never launched in those cases.
    result = ledger.grant(v.scope)
    if result.code not in ("GRANT_REGISTERED", "GRANT_ALREADY_EXISTS"):
        return AuthorizedDispatch(result.code, False, result.state)
    # On an existing grant, H14 can only deny a repeat claim. On a new
    # grant, H14 commits CLAIMED before dispatch and tolerates crashes.
    out = dispatch_synthetic_once(
        ledger, v.scope, raw_user_id=raw_user_id,
        broker_mode=trusted_broker_mode,
        scratch_log=scratch_log, timeout_secs=timeout_secs,
    )
    return AuthorizedDispatch(out.code, out.attempted, out.state)
