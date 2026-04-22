from sqlalchemy import BigInteger, String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class MediaItem(Base):
    __tablename__ = 'media_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String)
    subcategory: Mapped[str] = mapped_column(String, nullable=True)
    identifier: Mapped[str] = mapped_column(String, nullable=True)
    file_id: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    caption: Mapped[str] = mapped_column(String, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)