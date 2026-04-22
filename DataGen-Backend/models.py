from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database import Base

class Generator(Base):
    __tablename__ = "generators"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    interval_ms = Column(Integer, default=1000)
    is_api_enabled = Column(Boolean, default=False)
    is_message_broker_enabled = Column(Boolean, default=False)
    datetime_created = Column(DateTime, default=datetime.utcnow)
    
    nodes = relationship("Node", back_populates="generator", cascade="all, delete-orphan")

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    generator_id = Column(Integer, ForeignKey("generators.id", ondelete="CASCADE"))
    node_name = Column(String)
    data_type_enum = Column(String)
    generation_mode = Column(String)
    fixed_value = Column(String, nullable=True)
    value_list = Column(String, nullable=True)
    min_range = Column(Float, nullable=True)
    max_range = Column(Float, nullable=True)
    
    generator = relationship("Generator", back_populates="nodes")

class API(Base):
    __tablename__ = "apis"
    APIid = Column(Integer, primary_key=True, index=True)
    APIName = Column(String, nullable=False)
    TargetUrl = Column(String, nullable=False)
    Method = Column(String, default="POST")
    HeaderName = Column(String, nullable=True)
    HeaderValue = Column(String, nullable=True)
    DatetimeCreated = Column(DateTime, default=datetime.utcnow)
    # onupdate ensures the timestamp refreshes whenever the row is edited
    DatetimeUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MQTT(Base):
    __tablename__ = "mqtt_configs"
    MQTTid = Column(Integer, primary_key=True, index=True)
    MQTTName = Column(String, nullable=False)
    Topic = Column(String, nullable=False)
    DatetimeCreated = Column(DateTime, default=datetime.utcnow)
    DatetimeUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)