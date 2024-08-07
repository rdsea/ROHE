# generated by datamodel-codegen:
#   filename:  api__v1_openapi.json
#   timestamp: 2024-07-03T10:05:34+00:00

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, Field

from ...apimachinery.pkg.apis.meta import v1


class BoundObjectReference(BaseModel):
    api_version: str | None = Field(
        default=None, alias="apiVersion", description="API version of the referent."
    )
    kind: str | None = Field(
        default=None,
        description="Kind of the referent. Valid kinds are 'Pod' and 'Secret'.",
    )
    name: str | None = Field(default=None, description="Name of the referent.")
    uid: str | None = Field(default=None, description="UID of the referent.")


class TokenRequestSpec(BaseModel):
    audiences: list[str] = Field(
        ...,
        description="Audiences are the intendend audiences of the token. A recipient of a token must identify themself with an identifier in the list of audiences of the token, and otherwise should reject the token. A token issued for multiple audiences may be used to authenticate against any of the audiences listed but implies a high degree of trust between the target audiences.",
    )
    bound_object_ref: BoundObjectReference | None = Field(
        default=None,
        alias="boundObjectRef",
        description="BoundObjectRef is a reference to an object that the token will be bound to. The token will only be valid for as long as the bound object exists. NOTE: The API server's TokenReview endpoint will validate the BoundObjectRef, but other audiences may not. Keep ExpirationSeconds small if you want prompt revocation.",
    )
    expiration_seconds: int | None = Field(
        default=None,
        alias="expirationSeconds",
        description="ExpirationSeconds is the requested duration of validity of the request. The token issuer may return a token with a different validity duration so a client needs to check the 'expiration' field in a response.",
    )


class TokenRequestStatus(BaseModel):
    expiration_timestamp: AwareDatetime = Field(
        ...,
        alias="expirationTimestamp",
        description="ExpirationTimestamp is the time of expiration of the returned token.",
    )
    token: str = Field(..., description="Token is the opaque bearer token.")


class TokenRequest(BaseModel):
    api_version: str | None = Field(
        default=None,
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: str | None = Field(
        default=None,
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: v1.ObjectMeta | None = Field(
        default={},
        description="Standard object's metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )
    spec: TokenRequestSpec = Field(
        ..., description="Spec holds information about the request being evaluated"
    )
    status: TokenRequestStatus | None = Field(
        default={},
        description="Status is filled in by the server and indicates whether the token can be authenticated.",
    )
