from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    movies_dir: str = "/home/pi/movies"
    tvshows_dir: str = "/home/pi/tvshows"
    download_timeout: int = 3600
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]
    # Optional: set to enable TMDB movie lookups (free key at themoviedb.org)
    tmdb_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
