from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    cinetpay_api_key: str
    cinetpay_site_id: str
    cinetpay_base_url: str
    callback_url: str
    return_url: str

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()