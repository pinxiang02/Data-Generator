from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class GeneratorCreate(BaseModel):
    name: str
    description: str

class GeneratorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    interval_ms: Optional[int] = None
    is_api_enabled: Optional[bool] = None
    is_message_broker_enabled: Optional[bool] = None
    is_database_enabled: Optional[bool] = None
    selected_api_id: Optional[int] = None
    selected_mqtt_id: Optional[int] = None
    selected_db_id: Optional[int] = None

class APICreate(BaseModel):
    generator_id: Optional[int] = None  # Destinations are shared/global by default
    APIName: str
    TargetUrl: str
    Method: str = "POST"
    HeaderName: Optional[str] = None
    HeaderValue: Optional[str] = None

class APIUpdate(BaseModel):
    APIName: Optional[str] = None
    TargetUrl: Optional[str] = None
    Method: Optional[str] = None
    HeaderName: Optional[str] = None
    HeaderValue: Optional[str] = None

class MQTTCreate(BaseModel):
    generator_id: Optional[int] = None  # Destinations are shared/global by default
    MQTTName: str
    Host: str = "localhost"
    Port: int = 1883
    Topic: str

class MQTTUpdate(BaseModel):
    MQTTName: Optional[str] = None
    Host: Optional[str] = None
    Port: Optional[int] = None
    Topic: Optional[str] = None

class NodeBase(BaseModel):
    node_name: str
    data_type_enum: str = "String"
    generation_mode: str = "Fixed"
    fixed_value: Optional[str] = None
    value_list: Optional[str] = None
    min_range: Optional[float] = None
    max_range: Optional[float] = None

class DatabaseCreate(BaseModel):
    DBName: str
    DBType: str = "PostgreSQL"
    ConnectionString: str
    TableName: str

class DatabaseUpdate(BaseModel):
    DBName: Optional[str] = None
    DBType: Optional[str] = None
    ConnectionString: Optional[str] = None
    TableName: Optional[str] = None

class DatabaseTest(BaseModel):
    DBType: str = "PostgreSQL"
    ConnectionString: str
    TableName: Optional[str] = None

class EngineStartPayload(BaseModel):
    target_api_id: Optional[int] = None
    target_mqtt_id: Optional[int] = None
    target_db_id: Optional[int] = None
