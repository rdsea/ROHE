from pydantic import BaseModel

class MDBConf(BaseModel):
    url: str
    prefix: str
    username: str
    password: str