# generated by datamodel-codegen:
#   filename:  api__v1_openapi.json
#   timestamp: 2024-06-27T12:47:39+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ...apimachinery.pkg.apis.meta import v1


class Eviction(BaseModel):
    api_version: Optional[str] = Field(
        None,
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    delete_options: Optional[v1.DeleteOptions] = Field(
        None, alias="deleteOptions", description="DeleteOptions may be provided"
    )
    kind: Optional[str] = Field(
        None,
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: Optional[v1.ObjectMeta] = Field(
        {}, description="ObjectMeta describes the pod that is being evicted."
    )