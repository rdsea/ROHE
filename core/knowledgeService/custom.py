import pymongo, json
import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)



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
        if field !=None:
            queries[name] = {"conditions": query_criteria, "aggregation": aggregation, "field": field}
        else:
            queries[name] = {"conditions": query_criteria, "aggregation": aggregation}

    return queries, user_defined_aggregation

def construct_query(conditions):
    query_criteria = {}
    for condition in conditions:
        field_name = condition["field"]
        operator = condition["operator"]
        value = condition["value"]
        query_criteria[field_name] = {"$%s" % operator: value}
    return query_criteria

def calculate_metric(description, data):
    # Replace variables in the description with their values from the data dictionary
    expression = description.format(**data)
    # Evaluate the expression using eval()
    result = eval(expression)
    return result

def execute_metric_queries(collection, metric_description, model_name, limit = 10000, timestamp = None):

    # Parse metric description
    queries, overall_aggregation = parse_metric_description(metric_description)
    # Execute PyMongo queries for each variable
    metric_values = {}
    for name, query in queries.items():
        aggregation_pipeline = []
        if timestamp != None:
            aggregation_pipeline = [{"$match": {"model":{"$eq": model_name}, "timestamp": {"$lt": timestamp}}}, {"$sort": {"timestamp": pymongo.ASCENDING}}, {"$limit": limit}]
        else:
            aggregation_pipeline = [{"$match": {"model":{"$eq": model_name}}}, {"$sort": {"timestamp": pymongo.DESCENDING}}, {"$limit": limit}]
        
        aggregation_pipeline.append({"$match": query["conditions"]})
        if "field" in query:
            aggregation_pipeline.append({"$group": {"_id": None, "metric_value": {"$%s" % query["aggregation"]: "$%s" % query["field"]}}})
            result = collection.aggregate(aggregation_pipeline)
            metric_values[name] = list(result)[0]["metric_value"]
        else:
            aggregation_pipeline.append({"$group": {"_id": None, "%s" % query["aggregation"]: { "$sum": 1 }}})
            result = collection.aggregate(aggregation_pipeline)
            metric_values[name] = list(result)[0][query["aggregation"]]       
    return calculate_metric(overall_aggregation,metric_values)