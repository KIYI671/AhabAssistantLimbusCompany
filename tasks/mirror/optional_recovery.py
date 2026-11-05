"""Local theme-pack refresh timing with a two-second loading minimum."""


def operation_gap(config, minimum=0.15):
    """Respect the original zero-value fallback; never replace global timing."""
    return max(minimum, float(getattr(config, "mouse_action_interval", 0) or 0.5))


def theme_refresh_wait(config):
    # Allow the refreshed cards to settle before reading their names again.
    return max(2.0, operation_gap(config),
               float(getattr(config, "screenshot_interval", 0) or 0.85))
