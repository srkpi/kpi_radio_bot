from datetime import datetime
from sqlalchemy.orm import Mapped
from app.bot.models.base import Base


class BlockPhrase(Base):
    __tablename__ = "block_phrases"

    phrase: Mapped[str]
    set_by: Mapped[int]
    timestamp: Mapped[datetime]
