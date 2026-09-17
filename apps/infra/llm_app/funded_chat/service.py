from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from typing import Callable

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.infra.auth_app.account_linking.models import VerifiedEmail
from apps.infra.auth_app.models import EmailVerification
from apps.infra.llm_app.models import (
    FundedChatDailyQuota,
    FundedChatDailySpend,
    FundedChatRateBucket,
    FundedChatRequest,
)

from .config import FundedChatConfig
from .errors import ERROR_CATEGORIES, classify_provider_exception


class FundedChatDenied(Exception):
    """Sanitized policy refusal using the same seven-category client contract."""

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
    """Provider accounting returned by the injected, explicitly configured call."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    provider_cost_usd: Decimal


class FundedChatService:
    """Transactional funded allowance, abuse bucket, and spend reservation."""

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
        return VerifiedEmail.objects.filter(
            user=user, email__iexact=email
        ).exists() or (
            EmailVerification.objects.filter(
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
        """Claim one message and worst-case subsidy under database row locks."""

        if not self.config.enabled:
            raise FundedChatDenied("provider_outage")
        if not self._is_verified_real_user(user):
            raise FundedChatDenied("quota_reached")
        if not isinstance(idempotency_key, str) or not (
            1 <= len(idempotency_key) <= 200
        ):
            raise FundedChatDenied("provider_outage")

        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        request_hash = hashlib.sha256(request_body).hexdigest()
        day = self._day()
        now = self._utc_now()
        minute = now.replace(second=0, microsecond=0)

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
                            provider=self.config.provider,
                            model=self.config.litellm_model,
                            reserved_subsidy_usd=self.config.max_request_cost_usd,
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

            global_spend = self._locked_get_or_create(
                FundedChatDailySpend,
                day=day,
                scope=FundedChatDailySpend.GLOBAL_SCOPE,
            )
            provider_spend = self._locked_get_or_create(
                FundedChatDailySpend, day=day, scope=self.config.provider
            )
            reservation = self.config.max_request_cost_usd
            global_total = (
                global_spend.subsidy_cost_usd + global_spend.reserved_subsidy_usd
            )
            provider_total = (
                provider_spend.provider_cost_usd + provider_spend.reserved_subsidy_usd
            )
            if (
                global_total + reservation > self.config.global_daily_cap_usd
                or provider_total + reservation > self.config.provider_daily_cap_usd
            ):
                request.delete()
                raise FundedChatDenied("insufficient_balance")

            rate.request_count += 1
            rate.save(update_fields=["request_count"])
            quota.claimed_count += 1
            quota.save(update_fields=["claimed_count", "updated_at"])
            for spend in (global_spend, provider_spend):
                spend.reserved_subsidy_usd += reservation
                spend.save(update_fields=["reserved_subsidy_usd", "updated_at"])

            return Reservation(request, replayed=False)

    def _release_reservation(self, request: FundedChatRequest) -> None:
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
    def _stored_result(request: FundedChatRequest) -> ProviderResult:
        return ProviderResult(
            text=request.response_text,
            prompt_tokens=request.provider_prompt_tokens,
            completion_tokens=request.provider_completion_tokens,
            provider_cost_usd=request.provider_cost_usd,
        )

    def execute(
        self,
        user,
        *,
        idempotency_key: str,
        request_body: bytes,
        provider_call: Callable[[FundedChatConfig, bytes], ProviderResult],
    ) -> ProviderResult:
        """Execute at most one provider call for an idempotency key."""

        reservation = self.reserve(
            user, idempotency_key=idempotency_key, request_body=request_body
        )
        request = reservation.request
        if reservation.replayed:
            if request.status == FundedChatRequest.STATUS_SUCCEEDED:
                return self._stored_result(request)
            if request.status == FundedChatRequest.STATUS_FAILED:
                raise FundedChatDenied(
                    request.error_category or "provider_outage",
                    retry_after_seconds=request.retry_after_seconds,
                    support_id=request.support_id.hex,
                )
            raise FundedChatDenied("provider_outage", support_id=request.support_id.hex)

        try:
            result = provider_call(self.config, request_body)
            if not isinstance(result, ProviderResult):
                raise TypeError("provider adapter returned an invalid result")
            if (
                result.provider_cost_usd < 0
                or result.prompt_tokens < 0
                or result.completion_tokens < 0
            ):
                raise ValueError("provider adapter returned invalid accounting")
        except Exception as exc:
            classified = classify_provider_exception(exc)
            with transaction.atomic():
                locked = FundedChatRequest.objects.select_for_update().get(
                    pk=request.pk
                )
                if locked.status == FundedChatRequest.STATUS_RESERVED:
                    self._release_reservation(locked)
                    locked.status = FundedChatRequest.STATUS_FAILED
                    locked.error_category = classified.category
                    locked.retry_after_seconds = classified.retry_after_seconds
                    locked.reserved_subsidy_usd = Decimal("0")
                    locked.save(
                        update_fields=[
                            "status",
                            "error_category",
                            "retry_after_seconds",
                            "reserved_subsidy_usd",
                            "updated_at",
                        ]
                    )
            raise FundedChatDenied(
                classified.category,
                retry_after_seconds=classified.retry_after_seconds,
                support_id=request.support_id.hex,
            ) from None

        with transaction.atomic():
            locked = FundedChatRequest.objects.select_for_update().get(pk=request.pk)
            if locked.status == FundedChatRequest.STATUS_SUCCEEDED:
                return self._stored_result(locked)
            if locked.status != FundedChatRequest.STATUS_RESERVED:
                raise FundedChatDenied(
                    locked.error_category or "provider_outage",
                    retry_after_seconds=locked.retry_after_seconds,
                    support_id=locked.support_id.hex,
                )

            for scope in (FundedChatDailySpend.GLOBAL_SCOPE, locked.provider):
                spend = FundedChatDailySpend.objects.select_for_update().get(
                    day=locked.day, scope=scope
                )
                spend.reserved_subsidy_usd = max(
                    spend.reserved_subsidy_usd - locked.reserved_subsidy_usd,
                    Decimal("0"),
                )
                spend.provider_cost_usd += result.provider_cost_usd
                spend.subsidy_cost_usd += result.provider_cost_usd
                spend.save(
                    update_fields=[
                        "reserved_subsidy_usd",
                        "provider_cost_usd",
                        "subsidy_cost_usd",
                        "updated_at",
                    ]
                )

            locked.status = FundedChatRequest.STATUS_SUCCEEDED
            locked.provider_prompt_tokens = result.prompt_tokens
            locked.provider_completion_tokens = result.completion_tokens
            locked.provider_cost_usd = result.provider_cost_usd
            locked.subsidy_cost_usd = result.provider_cost_usd
            locked.response_text = result.text
            locked.reserved_subsidy_usd = Decimal("0")
            locked.save(
                update_fields=[
                    "status",
                    "provider_prompt_tokens",
                    "provider_completion_tokens",
                    "provider_cost_usd",
                    "subsidy_cost_usd",
                    "response_text",
                    "reserved_subsidy_usd",
                    "updated_at",
                ]
            )
            return self._stored_result(locked)
