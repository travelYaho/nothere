"""모든 API 스키마가 공통으로 상속하는 Pydantic 베이스 모델이다."""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    """snake_case 필드를 camelCase JSON 으로 노출하도록 기본 설정을 모아 둔다."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
