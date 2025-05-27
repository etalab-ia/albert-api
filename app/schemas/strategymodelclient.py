from app.schemas import BaseModel


class StrategyModelClient(BaseModel):
    model_name: str
    api_url: str
