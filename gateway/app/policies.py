import copy

DEFAULT_NOTIFICATION_POLICY = {
    "fall-detection": {
        "rules": [
            {
                "class_name": "Fine",
                "min_confidence": 0.70,
                "max_confidence": 1.01,
                "action": "warning",
                "cooldown_sec": 30,
            },
            {
                "class_name": "Fall",
                "min_confidence": 0.55,
                "max_confidence": 0.75,
                "action": "warning",
                "cooldown_sec": 20,
            },
            {
                "class_name": "Fall",
                "min_confidence": 0.75,
                "max_confidence": 1.01,
                "action": "alert",
                "cooldown_sec": 8,
            },
            ]
    },

    "fire-detection": {
        "rules": [
            {
                "class_name": "smoke",
                "min_confidence": 0.60,
                "max_confidence": 1.01,
                "action": "warning",
                "cooldown_sec": 30,
            },
            {
                "class_name": "fire",
                "min_confidence": 0.70,
                "max_confidence": 1.01,
                "action": "alert",
                "cooldown_sec": 10,
            },
        ]
    },

    "violence-detection": {
        "rules": [
            {
                "class_name": "violence",
                "min_confidence": 0.65,
                "max_confidence": 0.80,
                "action": "warning",
                "cooldown_sec": 20,
            },
            {
                "class_name": "violence",
                "min_confidence": 0.80,
                "max_confidence": 1.01,
                "action": "alert",
                "cooldown_sec": 8,
            },
        ]
    },

    "theft-detection": {
        "rules": [
            {
                "class_name": "Theft",
                "min_confidence": 0.4,
                "max_confidence": 0.6,
                "action": "warning",
                "cooldown_sec": 20,
            },
            {
                "class_name": "Theft",
                "min_confidence": 0.6,
                "max_confidence": 1.01,
                "action": "alert",
                "cooldown_sec": 10,
            },
        ]
    },

    "burglary-detection": {
        "rules": [
            {
                "class_name": "burglary",
                "min_confidence": 0.40,
                "max_confidence": 0.60,
                "action": "warning",
                "cooldown_sec": 20,
            },
            {
                "class_name": "burglary",
                "min_confidence": 0.60,
                "max_confidence": 1.01,
                "action": "alert",
                "cooldown_sec": 10,
            },
        ]
    },
}

CAMERA_POLICY_OVERRIDES = {
    # пример:
    # "cam-1": {
    #     "fire-detection": {
    #         "rules": [
    #             {
    #                 "class_name": "smoke",
    #                 "min_confidence": 0.80,
    #                 "max_confidence": 1.01,
    #                 "action": "warning",
    #                 "cooldown_sec": 60,
    #             },
    #             {
    #                 "class_name": "fire",
    #                 "min_confidence": 0.85,
    #                 "max_confidence": 1.01,
    #                 "action": "alert",
    #                 "cooldown_sec": 15,
    #             },
    #         ]
    #     }
    # }
}


def build_notification_policy(camera_id: str) -> dict:
    policy = copy.deepcopy(DEFAULT_NOTIFICATION_POLICY)

    overrides = CAMERA_POLICY_OVERRIDES.get(camera_id, {})
    for model_name, model_policy in overrides.items():
        policy[model_name] = copy.deepcopy(model_policy)

    return policy