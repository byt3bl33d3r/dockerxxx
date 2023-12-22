from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, List

DataT = TypeVar('DataT')

class Response(BaseModel, Generic[DataT]):
    data: Optional[List[DataT]] = None
