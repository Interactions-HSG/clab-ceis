croptop_recipe = {
    "fabric_blocks": ["FB1", "FB1", "FB2"],
    "processes": {
                   "sewing": {
                       "time": 1,
                       "resources": {"electricity": 5}
                       },
                   "steaming": {
                       "time": 3,
                       "resources": {"water": 2}
                   }
    }
}

FB1_recipe = {
    "material": "cotton",
    "amount": 2,
    "processes": {
        "sewing": {
            "time": 1,
            "resources": {"electricity": 5}
        },
        "steaming": {
            "time": 3,
            "resources": {"water": 2}
        }
    }
}

FB2_recipe = {
    "material": "polyester",
    "amount": 1,
    "processes": {
        "sewing": {
            "time": 1,
            "resources": {"electricity": 5}
        },
        "steaming": {
            "time": 3,
            "resources": {"water": 2}
        }
    }
}