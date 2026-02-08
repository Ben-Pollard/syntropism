import enum

from sqlalchemy.orm import Session

from .models import MarketState


class ResourceType(enum.Enum):
    CPU = "cpu"
    MEMORY = "memory"
    TOKENS = "tokens"
    ATTENTION = "attention"


class MarketManager:
    MIN_PRICE = 0.01
    MAX_PRICE = 1000.0
    HIGH_UTILIZATION_THRESHOLD = 0.8
    LOW_UTILIZATION_THRESHOLD = 0.2
    PRICE_INCREASE_FACTOR = 0.1  # 10% increase for high utilization
    PRICE_DECREASE_FACTOR = 0.05  # 5% decrease for low utilization

    @staticmethod
    def update_prices(session: Session):
        states = session.query(MarketState).all()
        for state in states:
            if state.current_utilization >= MarketManager.HIGH_UTILIZATION_THRESHOLD:
                state.current_market_price *= 1 + MarketManager.PRICE_INCREASE_FACTOR
            elif state.current_utilization <= MarketManager.LOW_UTILIZATION_THRESHOLD:
                state.current_market_price *= 1 - MarketManager.PRICE_DECREASE_FACTOR

            # Clamp prices
            state.current_market_price = max(
                MarketManager.MIN_PRICE, min(MarketManager.MAX_PRICE, state.current_market_price)
            )

    @staticmethod
    def get_market_state(session: Session, resource_type: ResourceType) -> MarketState:
        return session.query(MarketState).filter_by(resource_type=resource_type.value).first()
