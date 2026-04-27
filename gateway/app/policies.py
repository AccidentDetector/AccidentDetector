import copy

# Rules are evaluated top to bottom, first match wins.
# class_name is case-insensitive.
# '*' matches any class.
# action: 'ignore' | 'warning' | 'alert'

DEFAULT_NOTIFICATION_POLICY = {

    'fall-detection': {
        'rules': [
            # Stand — normal, never alert
            {
                'class_name'     : 'Stand',
                'min_confidence' : 0.0,
                'max_confidence' : 1.01,
                'action'         : 'ignore',
            },
            # Fine — ambiguous/crouching, never alert
            {
                'class_name'     : 'Fine',
                'min_confidence' : 0.0,
                'max_confidence' : 1.01,
                'action'         : 'ignore',
            },
            # Fall with medium confidence — warning
            {
                'class_name'     : 'Fall',
                'min_confidence' : 0.50,
                'max_confidence' : 0.75,
                'action'         : 'warning',
                'cooldown_sec'   : 20,
            },
            # Fall with high confidence — alert
            {
                'class_name'     : 'Fall',
                'min_confidence' : 0.75,
                'max_confidence' : 1.01,
                'action'         : 'alert',
                'cooldown_sec'   : 8,
            },
        ]
    },

    'fire-detection': {
        'rules': [
            # smoke — early warning
            {
                'class_name'     : 'smoke',
                'min_confidence' : 0.50,
                'max_confidence' : 1.01,
                'action'         : 'warning',
                'cooldown_sec'   : 30,
            },
            # fire — immediate alert
            {
                'class_name'     : 'fire',
                'min_confidence' : 0.60,
                'max_confidence' : 1.01,
                'action'         : 'alert',
                'cooldown_sec'   : 10,
            },
        ]
    },

    'violence-detection': {
        'rules': [
            # Normal — ignore
            {
                'class_name'     : 'Normal',
                'min_confidence' : 0.0,
                'max_confidence' : 1.01,
                'action'         : 'ignore',
            },
            # Violence with medium confidence — warning
            {
                'class_name'     : 'Violence',
                'min_confidence' : 0.45,
                'max_confidence' : 0.80,
                'action'         : 'warning',
                'cooldown_sec'   : 20,
            },
            # Violence with high confidence — alert
            {
                'class_name'     : 'Violence',
                'min_confidence' : 0.80,
                'max_confidence' : 1.01,
                'action'         : 'alert',
                'cooldown_sec'   : 8,
            },
        ]
    },

    'theft-detection': {
        'rules': [
            {
                'class_name'     : 'Theft',
                'min_confidence' : 0.40,
                'max_confidence' : 0.65,
                'action'         : 'warning',
                'cooldown_sec'   : 20,
            },
            {
                'class_name'     : 'Theft',
                'min_confidence' : 0.65,
                'max_confidence' : 1.01,
                'action'         : 'alert',
                'cooldown_sec'   : 10,
            },
        ]
    },

    'burglary-detection': {
        'rules': [
            {
                'class_name'     : 'burglary',
                'min_confidence' : 0.40,
                'max_confidence' : 0.65,
                'action'         : 'warning',
                'cooldown_sec'   : 20,
            },
            {
                'class_name'     : 'burglary',
                'min_confidence' : 0.65,
                'max_confidence' : 1.01,
                'action'         : 'alert',
                'cooldown_sec'   : 10,
            },
        ]
    },
}

# per-camera overrides — override specific model rules for specific cameras
CAMERA_POLICY_OVERRIDES: dict[str, dict] = {
    # example:
    # 'cam-entrance': {
    #     'fall-detection': {
    #         'rules': [
    #             {'class_name': 'Fall', 'min_confidence': 0.60, 'max_confidence': 1.01,
    #              'action': 'alert', 'cooldown_sec': 5},
    #         ]
    #     }
    # }
}


def build_notification_policy(camera_id: str) -> dict:
    policy = copy.deepcopy(DEFAULT_NOTIFICATION_POLICY)
    for model_name, model_policy in CAMERA_POLICY_OVERRIDES.get(camera_id, {}).items():
        policy[model_name] = copy.deepcopy(model_policy)
    return policy
