import time

import pymongo

COST_SCALE = float("1e-5")


def parse_metric_description(metric_description):
    variables = metric_description.get("variables")
    user_defined_aggregation = metric_description.get("overall_aggregation")

    queries = {}
    for variable in variables:
        name = variable.get("name")
        field = variable.get("field")
        conditions = variable["conditions"]
        aggregation = variable["aggregation"]
        query_criteria = construct_query(conditions)
        if field is not None:
            queries[name] = {
                "conditions": query_criteria,
                "aggregation": aggregation,
                "field": field,
            }
        else:
            queries[name] = {"conditions": query_criteria, "aggregation": aggregation}

    return queries, user_defined_aggregation


def construct_query(conditions):
    query_criteria = {}
    for condition in conditions:
        field_name = condition["field"]
        operator = condition["operator"]
        value = condition["value"]
        query_criteria[field_name] = {f"${operator}": value}
    return query_criteria


def calculate_metric(description, data):
    # Replace variables in the description with their values from the data dictionary
    expression = description.format(**data)
    # Evaluate the expression using eval()
    try:
        result = eval(expression)
    except Exception:
        result = -1
    return result


def execute_metric_queries(
    collection, metric_description, model_name, limit=10000, timestamp=None
):
    # Parse metric description
    queries, overall_aggregation = parse_metric_description(metric_description)
    # Execute PyMongo queries for each variable
    metric_values = {}
    for name, query in queries.items():
        aggregation_pipeline = []
        if timestamp is None:
            timestamp = int(time.time())
        aggregation_pipeline = [
            {"$match": {"timestamp": {"$lt": timestamp}}},
            {"$match": {"model": {"$eq": model_name}}},
            {"$sort": {"timestamp": pymongo.DESCENDING}},
            {"$limit": limit},
        ]

        aggregation_pipeline.append({"$match": query["conditions"]})
        if "field" in query:
            aggregation_pipeline.append(
                {
                    "$group": {
                        "_id": None,
                        "metric_value": {
                            "${}".format(query["aggregation"]): "${}".format(
                                query["field"]
                            )
                        },
                    }
                }
            )
            result = collection.aggregate(aggregation_pipeline)
            r_list = list(result)
            if r_list:
                metric_values[name] = r_list[0]["metric_value"]
            else:
                metric_values[name] = 0

        else:
            aggregation_pipeline.append(
                {
                    "$group": {
                        "_id": None,
                        "{}".format(query["aggregation"]): {"$sum": 1},
                    }
                }
            )
            result = collection.aggregate(aggregation_pipeline)
            r_list = list(result)
            if r_list:
                metric_values[name] = r_list[0][query["aggregation"]]
            else:
                metric_values[name] = 0
    return calculate_metric(overall_aggregation, metric_values)


def get_service_performance(collection, model_name, infrastructure):
    aggregation_pipeline = [
        {"$match": {"model_id": {"$eq": model_name}}},
        {"$match": {"infrastructure": {"$eq": infrastructure}}},
        {"$sort": {"timestamp": pymongo.DESCENDING}},
        {"$limit": 1},
    ]
    result = collection.aggregate(aggregation_pipeline)
    r_list = list(result)
    if r_list:
        return r_list[0]
    else:
        return 0


def get_service_cost(
    service_cost_collection, infrastructure_cost_collection, model_name, infrastructure
):
    aggregation_pipeline = [
        {"$match": {"model": {"$eq": model_name}}},
        {"$sort": {"timestamp": pymongo.DESCENDING}},
        {"$limit": 1},
    ]
    service_cost_response = service_cost_collection.aggregate(aggregation_pipeline)
    r_list = list(service_cost_response)
    if r_list:
        service_cost = r_list[0]["baseCost"]
    else:
        service_cost = float("inf")

    aggregation_pipeline = [
        {"$match": {"infrastructure": {"$eq": infrastructure}}},
        {"$sort": {"timestamp": pymongo.DESCENDING}},
        {"$limit": 1},
    ]
    infrastructure_cost_response = infrastructure_cost_collection.aggregate(
        aggregation_pipeline
    )
    r_list = list(infrastructure_cost_response)
    if r_list:
        infrastructure_cost = r_list[0]["baseCost"]
    else:
        infrastructure_cost = float("inf")
    return COST_SCALE * (infrastructure_cost + service_cost)
