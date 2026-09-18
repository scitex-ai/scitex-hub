from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from typing import Callable

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.infra.auth_app.account_linking.models import VerifiedEmail
from apps.infra.auth_app.models import EmailVerification
from apps.infra.llm_app.models import (
    FundedChatDailyQuota,
    FundedChatDailySpend,
    FundedChatRateBucket,
    FundedChatRequest,
)

from .config import FundedChatConfig, FundedChatConfigurationError, quantize_money
from .errors import ERROR_CATEGORIES, classify_provider_exception


class FundedChatDenied(Exception):
    """Sanitized policy refusal using the stable client error contract."""

    def __init__(
        self,
        category: str,
        *,
        retry_after_seconds: int | None = None,
        support_id: str = "",
    ) -> None:
        if category not in ERROR_CATEGORIES:
            raise ValueError("unsupported funded-chat error category")
        self.category = category
        self.retry_after_seconds = retry_after_seconds
        self.support_id = support_id
        super().__init__(category)


@dataclass(frozen=True, slots=True)
class AllowanceSnapshot:
    category: str | None
    remaining: int | None
    reset_at: str
    model: str
    total: int

    def as_payload(self) -> dict[str, str | int | None]:
        state = (
            "unknown"
            if self.remaining is None
            else "exhausted"
            if self.remaining == 0
            else "available"
        )
        return {
            "category": self.category,
            "remaining": self.remaining,
            "reset_at": self.reset_at,
            "model": self.model,
            "total": self.total,
            "state": state,
        }


@dataclass(frozen=True, slots=True)
class Reservation:
    request: FundedChatRequest
    replayed: bool


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Provider accounting returned by the injected, configured call."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    provider_cost_usd: Decimal


class _InvalidProviderResult(Exception):
    pass


class FundedChatService:
    """Crash-safe funded allowance and spend ledger.

    A request is durable before dispatch. Only exceptions explicitly marked as
    definitely pre-dispatch release quota and spend. Every unknown outcome after
    the dispatch phase retains its reservation until reconciliation.
    """

    def __init__(
        self,
        *,
        config: FundedChatConfig,
        now: Callable[[], datetime] = timezone.now,
    ) -> None:
        self.config = config
        self._now = now

    def _utc_now(self) -> datetime:
        value = self._now()
        if timezone.is_naive(value):
            value = value.replace(tzinfo=dt_timezone.utc)
        return value.astimezone(dt_timezone.utc)

    def _day(self):
        return self._utc_now().date()

    def _reset_at(self) -> str:
        reset = datetime.combine(
            self._day() + timedelta(days=1), time.min, tzinfo=dt_timezone.utc
        )
        return reset.isoformat().replace("+00:00", "Z")

    def _lease_expires_at(self) -> datetime:
        return self._utc_now() + timedelta(
            seconds=self.config.reservation_lease_seconds
        )

    @staticmethod
    def _is_verified_real_user(user) -> bool:
        if (
            not user
            or not user.is_authenticated
            or not user.is_active
            or not user.email
        ):
            return False
        email = user.email.strip().lower()
        return (
            VerifiedEmail.objects.filter(user=user, email__iexact=email).exists()
            or EmailVerification.objects.filter(
                user=user, email__iexact=email, is_verified=True
            ).exists()
        )

    def snapshot(self, user) -> AllowanceSnapshot:
        model = (
            self.config.litellm_model
            if self.config.provider and self.config.model
            else ""
        )
        if not self.config.enabled:
            return AllowanceSnapshot(
                "provider_outage",
                None,
                self._reset_at(),
                model,
                self.config.daily_limit,
            )
        if not self._is_verified_real_user(user):
            return AllowanceSnapshot(
                "quota_reached",
                None,
                self._reset_at(),
                model,
                self.config.daily_limit,
            )
        count = (
            FundedChatDailyQuota.objects.filter(user=user, day=self._day())
            .values_list("claimed_count", flat=True)
            .first()
            or 0
        )
        remaining = max(self.config.daily_limit - count, 0)
        return AllowanceSnapshot(
            "quota_reached" if remaining == 0 else None,
            remaining,
            self._reset_at(),
            model,
            self.config.daily_limit,
        )

    @staticmethod
    def _locked_get_or_create(model, **lookup):
        try:
            return model.objects.select_for_update().get(**lookup)
        except model.DoesNotExist:
            try:
                with transaction.atomic():
                    return model.objects.create(**lookup)
            except IntegrityError:
                return model.objects.select_for_update().get(**lookup)

    def reserve(
        self, user, *, idempotency_key: str, request_body: bytes
    ) -> Reservation:
        """Claim one message and a quantized worst-case subsidy under row locks."""

        if not self.config.enabled:
            raise FundedChatDenied("provider_outage")
        if not self._is_verified_real_user(user):
            raise FundedChatDenied("quota_reached")
        if not isinstance(idempotency_key, str) or not (
            1 <= len(idempotency_key) <= 200
        ):
            raise FundedChatDenied("provider_outage")
        if (
            not isinstance(request_body, bytes)
            or len(request_body) > self.config.max_request_bytes
        ):
            raise FundedChatDenied("provider_outage")

        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        request_hash = hashlib.sha256(request_body).hexdigest()
        dispatch_key = hashlib.sha256(f"{user.pk}:{key_hash}".encode()).hexdigest()
        day = self._day()
        now = self._utc_now()
        minute = now.replace(second=0, microsecond=0)
        reservation_amount = quantize_money(
            self.config.max_request_cost_usd, name="request reservation"
        )

        with transaction.atomic():
            try:
                existing = FundedChatRequest.objects.select_for_update().get(
                    user=user, idempotency_key_hash=key_hash
                )
            except FundedChatRequest.DoesNotExist:
                try:
                    with transaction.atomic():
                        request = FundedChatRequest.objects.create(
                            user=user,
                            day=day,
                            idempotency_key_hash=key_hash,
                            request_hash=request_hash,
                            dispatch_key=dispatch_key,
                            lease_expires_at=self._lease_expires_at(),
                            provider=self.config.provider,
                            model=self.config.litellm_model,
                            reserved_subsidy_usd=reservation_amount,
                        )
                except IntegrityError:
                    existing = FundedChatRequest.objects.select_for_update().get(
                        user=user, idempotency_key_hash=key_hash
                    )
                else:
                    existing = None

            if existing is not None:
                if existing.request_hash != request_hash:
                    raise FundedChatDenied(
                        "provider_outage", support_id=existing.support_id.hex
                    )
                if (
                    existing.status == FundedChatRequest.STATUS_RESERVED
                    and existing.phase == FundedChatRequest.PHASE_PRE_DISPATCH
                    and existing.lease_expires_at <= now
                ):
                    existing.lease_expires_at = self._lease_expires_at()
                    existing.save(update_fields=["lease_expires_at", "updated_at"])
                    return Reservation(existing, replayed=False)
                return Reservation(existing, replayed=True)

            rate = self._locked_get_or_create(
                FundedChatRateBucket, user=user, window_start=minute
            )
            if rate.request_count >= self.config.requests_per_minute:
                request.delete()
                raise FundedChatDenied(
                    "rate_limit", retry_after_seconds=max(60 - now.second, 1)
                )

            quota = self._locked_get_or_create(FundedChatDailyQuota, user=user, day=day)
            if quota.claimed_count >= self.config.daily_limit:
                request.delete()
                raise FundedChatDenied("quota_reached")

            # Lock ordering is always global then provider, across every user.
            global_spend = self._locked_get_or_create(
                FundedChatDailySpend,
                day=day,
                scope=FundedChatDailySpend.GLOBAL_SCOPE,
            )
            provider_spend = self._locked_get_or_create(
                FundedChatDailySpend, day=day, scope=self.config.provider
            )
            global_total = (
                global_spend.subsidy_cost_usd + global_spend.reserved_subsidy_usd
            )
            provider_total = (
                provider_spend.provider_cost_usd + provider_spend.reserved_subsidy_usd
            )
            if (
                global_total + reservation_amount > self.config.global_daily_cap_usd
                or provider_total + reservation_amount
                > self.config.provider_daily_cap_usd
            ):
                request.delete()
                raise FundedChatDenied("insufficient_balance")

            rate.request_count += 1
            rate.save(update_fields=["request_count"])
            quota.claimed_count += 1
            quota.save(update_fields=["claimed_count", "updated_at"])
            for spend in (global_spend, provider_spend):
                spend.reserved_subsidy_usd += reservation_amount
                spend.save(update_fields=["reserved_subsidy_usd", "updated_at"])

            return Reservation(request, replayed=False)

    @staticmethod
    def _stored_result(request: FundedChatRequest) -> ProviderResult:
        return ProviderResult(
            text=request.response_text,
            prompt_tokens=request.provider_prompt_tokens,
            completion_tokens=request.provider_completion_tokens,
            provider_cost_usd=request.provider_cost_usd,
        )

    @staticmethod
    def _release_reservation(request: FundedChatRequest) -> None:
        quota = FundedChatDailyQuota.objects.select_for_update().get(
            user=request.user, day=request.day
        )
        quota.claimed_count = max(quota.claimed_count - 1, 0)
        quota.save(update_fields=["claimed_count", "updated_at"])
        for scope in (FundedChatDailySpend.GLOBAL_SCOPE, request.provider):
            spend = FundedChatDailySpend.objects.select_for_update().get(
                day=request.day, scope=scope
            )
            spend.reserved_subsidy_usd = max(
                spend.reserved_subsidy_usd - request.reserved_subsidy_usd,
                Decimal("0"),
            )
            spend.save(update_fields=["reserved_subsidy_usd", "updated_at"])

    @staticmethod
    def _commit_cost(request: FundedChatRequest, cost: Decimal) -> None:
        for scope in (FundedChatDailySpend.GLOBAL_SCOPE, request.provider):
            spend = FundedChatDailySpend.objects.select_for_update().get(
                day=request.day, scope=scope
            )
            spend.reserved_subsidy_usd = max(
                spend.reserved_subsidy_usd - request.reserved_subsidy_usd,
                Decimal("0"),
            )
            spend.provider_cost_usd += cost
            spend.subsidy_cost_usd += cost
            spend.save(
                update_fields=[
                    "reserved_subsidy_usd",
                    "provider_cost_usd",
                    "subsidy_cost_usd",
                    "updated_at",
                ]
            )

    def _mark_dispatching(self, request_id: int) -> FundedChatRequest:
        with transaction.atomic():
            request = FundedChatRequest.objects.select_for_update().get(pk=request_id)
            if request.status != FundedChatRequest.STATUS_RESERVED:
                raise FundedChatDenied(
                    request.error_category or "provider_outage",
                    support_id=request.support_id.hex,
                )
            request.status = FundedChatRequest.STATUS_DISPATCHING
            request.phase = FundedChatRequest.PHASE_DISPATCHED
            request.dispatched_at = self._utc_now()
            request.lease_expires_at = self._lease_expires_at()
            request.save(
                update_fields=[
                    "status",
                    "phase",
                    "dispatched_at",
                    "lease_expires_at",
                    "updated_at",
                ]
            )
            return request

    def _mark_pre_dispatch_failed(self, request_id: int, exc: Exception) -> None:
        classified = classify_provider_exception(exc)
        with transaction.atomic():
            request = FundedChatRequest.objects.select_for_update().get(pk=request_id)
            if request.status not in {
                FundedChatRequest.STATUS_RESERVED,
                FundedChatRequest.STATUS_DISPATCHING,
            }:
                return
            self._release_reservation(request)
            request.status = FundedChatRequest.STATUS_FAILED
            request.phase = FundedChatRequest.PHASE_PRE_DISPATCH
            request.error_category = classified.category
            request.retry_after_seconds = classified.retry_after_seconds
            request.reserved_subsidy_usd = Decimal("0")
            request.save(
                update_fields=[
                    "status",
                    "phase",
                    "error_category",
                    "retry_after_seconds",
                    "reserved_subsidy_usd",
                    "updated_at",
                ]
            )

    def _mark_reconciliation_required(
        self, request_id: int, exc: BaseException
    ) -> None:
        classified = classify_provider_exception(exc)
        with transaction.atomic():
            request = FundedChatRequest.objects.select_for_update().get(pk=request_id)
            if request.status not in {
                FundedChatRequest.STATUS_DISPATCHING,
                FundedChatRequest.STATUS_RECONCILIATION_REQUIRED,
            }:
                return
            request.status = FundedChatRequest.STATUS_RECONCILIATION_REQUIRED
            request.phase = FundedChatRequest.PHASE_DISPATCHED
            request.error_category = classified.category
            request.retry_after_seconds = classified.retry_after_seconds
            request.reconciliation_required_at = self._utc_now()
            request.save(
                update_fields=[
                    "status",
                    "phase",
                    "error_category",
                    "retry_after_seconds",
                    "reconciliation_required_at",
                    "updated_at",
                ]
            )

    @staticmethod
    def _normalize_result(result: ProviderResult) -> ProviderResult:
        if not isinstance(result, ProviderResult):
            raise _InvalidProviderResult
        try:
            cost = quantize_money(result.provider_cost_usd, name="provider actual cost")
            prompt_tokens = int(result.prompt_tokens)
            completion_tokens = int(result.completion_tokens)
        except (
            FundedChatConfigurationError,
            TypeError,
            ValueError,
            OverflowError,
        ) as exc:
            raise _InvalidProviderResult from exc
        if (
            prompt_tokens < 0
            or completion_tokens < 0
            or prompt_tokens > 2_147_483_647
            or completion_tokens > 2_147_483_647
            or not isinstance(result.text, str)
        ):
            raise _InvalidProviderResult
        return ProviderResult(
            text=result.text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            provider_cost_usd=cost,
        )

    def _persist_provider_result(
        self, request_id: int, result: ProviderResult
    ) -> FundedChatRequest:
        with transaction.atomic():
            request = FundedChatRequest.objects.select_for_update().get(pk=request_id)
            if request.status == FundedChatRequest.STATUS_PROVIDER_SUCCEEDED:
                return request
            if request.status != FundedChatRequest.STATUS_DISPATCHING:
                raise FundedChatDenied(
                    request.error_category or "provider_outage",
                    support_id=request.support_id.hex,
                )
            request.status = FundedChatRequest.STATUS_PROVIDER_SUCCEEDED
            request.phase = FundedChatRequest.PHASE_RESPONSE_RECEIVED
            request.provider_responded_at = self._utc_now()
            request.provider_prompt_tokens = result.prompt_tokens
            request.provider_completion_tokens = result.completion_tokens
            request.provider_cost_usd = result.provider_cost_usd
            request.subsidy_cost_usd = result.provider_cost_usd
            request.response_text = result.text
            request.save(
                update_fields=[
                    "status",
                    "phase",
                    "provider_responded_at",
                    "provider_prompt_tokens",
                    "provider_completion_tokens",
                    "provider_cost_usd",
                    "subsidy_cost_usd",
                    "response_text",
                    "updated_at",
                ]
            )
            return request

    def _finalize_succeeded_request(self, request_id: int) -> FundedChatRequest:
        with transaction.atomic():
            request = FundedChatRequest.objects.select_for_update().get(pk=request_id)
            if request.status in {
                FundedChatRequest.STATUS_SUCCEEDED,
                FundedChatRequest.STATUS_ACCOUNTING_ANOMALY,
            }:
                return request
            if request.status != FundedChatRequest.STATUS_PROVIDER_SUCCEEDED:
                raise FundedChatDenied(
                    request.error_category or "provider_outage",
                    support_id=request.support_id.hex,
                )
            reservation = request.reserved_subsidy_usd
            actual = request.provider_cost_usd
            self._commit_cost(request, actual)
            request.reserved_subsidy_usd = Decimal("0")
            if actual > reservation:
                request.status = FundedChatRequest.STATUS_ACCOUNTING_ANOMALY
                request.error_category = "provider_outage"
            else:
                request.status = FundedChatRequest.STATUS_SUCCEEDED
            request.save(
                update_fields=[
                    "status",
                    "error_category",
                    "reserved_subsidy_usd",
                    "updated_at",
                ]
            )
            return request

    @staticmethod
    def _denied_from_request(request: FundedChatRequest) -> FundedChatDenied:
        return FundedChatDenied(
            request.error_category or "provider_outage",
            retry_after_seconds=request.retry_after_seconds,
            support_id=request.support_id.hex,
        )

    def _handle_replay(self, request: FundedChatRequest) -> ProviderResult:
        request.refresh_from_db()
        if request.status == FundedChatRequest.STATUS_PROVIDER_SUCCEEDED:
            request = self._finalize_succeeded_request(request.pk)
        if request.status == FundedChatRequest.STATUS_SUCCEEDED:
            return self._stored_result(request)
        raise self._denied_from_request(request)

    def execute(
        self,
        user,
        *,
        idempotency_key: str,
        request_body: bytes,
        provider_call: Callable[[FundedChatConfig, bytes, str], ProviderResult],
    ) -> ProviderResult:
        """Execute at most one provider call for an idempotency key."""

        reservation = self.reserve(
            user, idempotency_key=idempotency_key, request_body=request_body
        )
        request = reservation.request
        if reservation.replayed:
            return self._handle_replay(request)

        request = self._mark_dispatching(request.pk)
        try:
            raw_result = provider_call(self.config, request_body, request.dispatch_key)
            result = self._normalize_result(raw_result)
        except asyncio.CancelledError as exc:
            self._mark_reconciliation_required(request.pk, exc)
            raise
        except Exception as exc:
            classified = classify_provider_exception(exc)
            if bool(getattr(exc, "definitely_not_dispatched", False)):
                self._mark_pre_dispatch_failed(request.pk, exc)
            else:
                self._mark_reconciliation_required(request.pk, exc)
            raise FundedChatDenied(
                classified.category,
                retry_after_seconds=classified.retry_after_seconds,
                support_id=request.support_id.hex,
            ) from None

        self._persist_provider_result(request.pk, result)
        finalized = self._finalize_succeeded_request(request.pk)
        if finalized.status == FundedChatRequest.STATUS_ACCOUNTING_ANOMALY:
            raise self._denied_from_request(finalized)
        return self._stored_result(finalized)

    def reconcile_stale_requests(self, *, limit: int = 100) -> int:
        """Finalize durable responses and conservatively settle expired leases."""

        if limit <= 0:
            return 0
        now = self._utc_now()
        ids = list(
            FundedChatRequest.objects.filter(
                status__in=[
                    FundedChatRequest.STATUS_PROVIDER_SUCCEEDED,
                    FundedChatRequest.STATUS_RESERVED,
                    FundedChatRequest.STATUS_DISPATCHING,
                    FundedChatRequest.STATUS_RECONCILIATION_REQUIRED,
                ]
            )
            .filter(
                # Provider responses are immediately recoverable; other phases
                # are only touched once their exclusive execution lease expires.
                Q(status=FundedChatRequest.STATUS_PROVIDER_SUCCEEDED)
                | Q(lease_expires_at__lte=now)
            )
            .order_by("created_at")
            .values_list("pk", flat=True)[:limit]
        )
        reconciled = 0
        for request_id in ids:
            with transaction.atomic():
                request = FundedChatRequest.objects.select_for_update().get(
                    pk=request_id
                )
                if request.status == FundedChatRequest.STATUS_PROVIDER_SUCCEEDED:
                    # Release this lock before the finalizer opens its own atomic block.
                    pass
                elif (
                    request.status == FundedChatRequest.STATUS_RESERVED
                    and request.phase == FundedChatRequest.PHASE_PRE_DISPATCH
                    and request.lease_expires_at <= now
                ):
                    self._release_reservation(request)
                    request.status = FundedChatRequest.STATUS_FAILED
                    request.error_category = "provider_outage"
                    request.reserved_subsidy_usd = Decimal("0")
                    request.save(
                        update_fields=[
                            "status",
                            "error_category",
                            "reserved_subsidy_usd",
                            "updated_at",
                        ]
                    )
                    reconciled += 1
                    continue
                elif (
                    request.status
                    in {
                        FundedChatRequest.STATUS_DISPATCHING,
                        FundedChatRequest.STATUS_RECONCILIATION_REQUIRED,
                    }
                    and request.lease_expires_at <= now
                ):
                    conservative_cost = request.reserved_subsidy_usd
                    self._commit_cost(request, conservative_cost)
                    request.status = FundedChatRequest.STATUS_RECONCILED
                    request.phase = FundedChatRequest.PHASE_RECONCILED
                    request.error_category = "provider_outage"
                    request.provider_cost_usd = conservative_cost
                    request.subsidy_cost_usd = conservative_cost
                    request.reserved_subsidy_usd = Decimal("0")
                    request.save(
                        update_fields=[
                            "status",
                            "phase",
                            "error_category",
                            "provider_cost_usd",
                            "subsidy_cost_usd",
                            "reserved_subsidy_usd",
                            "updated_at",
                        ]
                    )
                    reconciled += 1
                    continue
                else:
                    continue
            self._finalize_succeeded_request(request_id)
            reconciled += 1
        return reconciled
