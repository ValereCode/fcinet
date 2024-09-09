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
        
class CheckPay(BaseModel):
    trans_id: str
    user_id: str
    
    class config:
        from_attributes = True
        
        
class PaymentNotification(BaseModel):
    transaction_id: str
    apikey: str
    site_id: str
    amount: int
    currency: str
    status: str
    payment_method: str
    description: str
    operator_id: str
    payment_date: str
    fund_availability_date: str
    metadata: str