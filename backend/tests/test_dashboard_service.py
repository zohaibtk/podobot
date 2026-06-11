from datetime import UTC, datetime, timedelta

from app.modules.dashboard.service import DashboardWindow, RealAnalyticsProvider


def test_current_bucket_end_includes_rest_of_day_for_publishing_queue() -> None:
    now = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    provider = RealAnalyticsProvider(
        session=None,  # type: ignore[arg-type]
        window=DashboardWindow(
            range="30d",
            group_by="day",
            now=now,
            start=now - timedelta(days=30),
            previous_start=now - timedelta(days=60),
        ),
    )

    assert provider._current_bucket_end() == datetime(
        2026,
        6,
        8,
        23,
        59,
        59,
        999999,
        tzinfo=UTC,
    )


def test_current_bucket_end_uses_current_window_week() -> None:
    now = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    start = now - timedelta(days=30)
    provider = RealAnalyticsProvider(
        session=None,  # type: ignore[arg-type]
        window=DashboardWindow(
            range="90d",
            group_by="week",
            now=now,
            start=start,
            previous_start=start - timedelta(days=90),
        ),
    )

    elapsed_days = (now - start).days
    expected_bucket_start = start + timedelta(days=(elapsed_days // 7) * 7)
    assert provider._current_bucket_end() == expected_bucket_start + timedelta(
        days=7,
        microseconds=-1,
    )
