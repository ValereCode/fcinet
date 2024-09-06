from pydantic import BaseModel, EmailStr

class UserPayload(BaseModel):
    amount: int
    trans_id: str
    description: str
    customer_name: str
    customer_email: EmailStr
    
    class Config:
        from_attributes = True
        
class CheckPay(BaseModel):
    trans_id: str
    user_id: str
    
    class config:
        from_attributes = True