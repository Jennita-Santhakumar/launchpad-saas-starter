from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base for request/response models. Disables pydantic's `model_` protected-namespace
    warning since this API legitimately has fields like `model_config`-adjacent domain names."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)
