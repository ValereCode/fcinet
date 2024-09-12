from pydantic import BaseModel, EmailStr

class UserPayload(BaseModel):
    amount: int
    trans_id: str
    description: str
    customer_name: str
    customer_email: EmailStr
    metadata: str
    
    class Config:
        from_attributes = True


class VerifyTransaction(BaseModel):
    trans_id: str
    
    class Config:
        from_attributes = True