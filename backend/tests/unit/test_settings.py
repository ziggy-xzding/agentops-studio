from app.config import Settings


def test_settings_default_to_zero_config_local_services() -> None:
    settings = Settings()

    assert settings.database_url == "sqlite:///./agentops.db"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_settings_parse_comma_separated_origins() -> None:
    settings = Settings(cors_origins="https://demo.example.com,http://localhost:5173")

    assert settings.cors_origins == ["https://demo.example.com", "http://localhost:5173"]
