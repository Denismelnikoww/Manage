from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func
from app.core.database import Base

class LabWork(Base):
    """
    SQLAlchemy model for Laboratory Work (WBS 4.2.2).
    Mapped to table 'lab_works'.
    """
    __tablename__ = "lab_works"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_num = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False, index=True)
    group_name = Column(String(50), nullable=False, default="ВПР42", index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
