from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ChatLog(Base):
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    username = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChatLog(user={self.username}, date={self.timestamp})>"

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id_str = Column(String, unique=True, index=True) # e.g. BN-FEB-26-001
    date = Column(String) # YYYY-MM-DD
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class PhotoMetadata(Base):
    __tablename__ = "photo_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    file_unique_id = Column(String, unique=True, index=True)
    file_path = Column(String)
    analysis = Column(Text)
    caption = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    date_str = Column(String, index=True) # YYYY-MM-DD required for filtering by day

class ReportCounter(Base):
    __tablename__ = "report_counters"
    
    id = Column(Integer, primary_key=True, index=True)
    month_key = Column(String, unique=True) # e.g. 2026-02
    count = Column(Integer, default=0)

class BotSettings(Base):
    __tablename__ = "bot_settings"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String)
