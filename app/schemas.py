from pydantic import BaseModel, EmailStr

class UserPayload(BaseModel):
    amount: int
    trans_id: str
    description: str
    customer_name: str
    customer_email: EmailStr
    metadata: str = None
    
    class Config:
        from_attributes = True
        
class CheckPay(BaseModel):
    trans_id: str
    user_id: str
    
    class config:
        from_attributes = True
        
        
class PaymentNotification(BaseModel):
    transaction_id: str
    apikey: str
    site_id: str
    amount: str = None
    currency: str = None
    status: str = None
    payment_method: str = None
    description: str = None
    operator_id: str = None
    payment_date: str = None
    fund_availability_date: str = None
    metadata: str = None