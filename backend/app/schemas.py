from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CheckType(str, Enum):
    PING = "ping"
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    TRACEROUTE = "traceroute"
    DNS_A = "dns_a"
    DNS_AAAA = "dns_aaaa"
    DNS_MX = "dns_mx"
    DNS_NS = "dns_ns"
    DNS_TXT = "dns_txt"
    DNS_CNAME = "dns_cname"

class CheckCreate(BaseModel):
    target: str
    check_types: List[CheckType]

class CheckResponse(BaseModel):
    id: str
    target: str
    check_types: List[CheckType]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class CheckResultResponse(BaseModel):
    id: int
    check_type: CheckType
    success: bool
    result_data: Dict[str, Any]
    response_time: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    agent_name: Optional[str]
    
    class Config:
        from_attributes = True

class CheckWithResults(CheckResponse):
    results: List[CheckResultResponse] = []

class AgentCreate(BaseModel):
    name: str
    location: Optional[str] = None
    token: str

class AgentResponse(BaseModel):
    id: str
    name: str
    location: Optional[str]
    is_active: bool
    last_heartbeat: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True