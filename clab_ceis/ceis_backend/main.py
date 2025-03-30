from utils import get_bindings
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.get("/croptop")
def get_info_croptop():
    try:
        bindings = get_bindings("getTopData")

        print(bindings)
        data = [
            {
                "recipe": item.get("recipeName", {}).get("value"),
                "fabricBlockDesign": item.get("fabricBlockDesignName", {}).get("value"),
                "requiredAmount": int(item.get("requiredAmount", {}).get("value", 0)),
                "availableAmount": int(item.get("availableAmount", {}).get("value", 0)),
            }
            for item in bindings
        ]
        print("data", data)
        return {}
    except Exception as e:
        return {"error": str(e)}

    # return {
    #     "alternatives": [
    #         {
    #             "price": 25,
    #             "co2eq": 33,
    #             "timestamp": 1707985660,
    #         },
    #         {
    #             "price": 40,
    #             "co2eq": 20,
    #             "timestamp": 1708985660,
    #         },
    #     ]
    # }
