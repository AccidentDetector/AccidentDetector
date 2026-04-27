from typing import Any

ALLOWED_ACTIONS = {'ignore', 'warning', 'alert'}


def resolve_action(
    camera,
    model_name: str,
    result: dict[str, Any],
) -> tuple[str, float, str, float | None]:
    """
    Determine what action to take based on detection result and camera policy.

    Returns: (action, confidence, class_name, cooldown_sec)
    action is one of: 'ignore', 'warning', 'alert'
    """
    detections = result.get('detections', [])
    top = max(detections, key=lambda d: d.get('confidence', 0.0), default=None)

    confidence = float(top.get('confidence', 0.0)) if top else 0.0
    class_name = str(top.get('class_name', 'unknown')) if top else 'unknown'

    if not detections:
        return 'ignore', 0.0, 'unknown', None

    model_policy = camera.notification_policy.get(model_name, {})
    rules        = model_policy.get('rules', [])

    for rule in rules:
        rule_class = rule.get('class_name', '*')

        # wildcard or case-insensitive match
        if rule_class != '*' and rule_class.lower() != class_name.lower():
            continue

        min_c = float(rule.get('min_confidence', 0.0))
        max_c = float(rule.get('max_confidence', 1.01))

        if min_c <= confidence < max_c:
            action = str(rule.get('action', 'ignore')).lower()
            if action not in ALLOWED_ACTIONS:
                action = 'ignore'
            raw_cooldown = rule.get('cooldown_sec')
            cooldown_sec = float(raw_cooldown) if raw_cooldown is not None else None
            return action, confidence, class_name, cooldown_sec

    # no rule matched — ignore by default
    return 'ignore', confidence, class_name, None
