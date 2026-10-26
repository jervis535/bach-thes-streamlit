"""Usage counting for the app's services (stored in public.use_count)."""

import logging

from services.auth import get_client

logger = logging.getLogger(__name__)

SERVICES = ("clustering", "panel_regression")


def record_use(service: str) -> None:
    """Add one to today's counter for `service`.

    The increment happens inside Postgres (see use_count_setup.sql), so
    simultaneous users can't overwrite each other's counts. A failure here is
    logged but never raised: counting must not break the feature being used.
    """
    if service not in SERVICES:
        raise ValueError(f"Unknown service: {service!r}")

    try:
        get_client().rpc("increment_use_count", {"service": service}).execute()
    except Exception:
        logger.warning("Could not record usage for %s", service, exc_info=True)