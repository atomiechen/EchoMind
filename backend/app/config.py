from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


# ref: https://github.com/pydantic/pydantic/discussions/4170#discussioncomment-9668111
class YamlBaseSettings(BaseSettings):
    # you can specify the configuration file path `yaml_file` during initialization
    yaml_file: Optional[Path] = None

    # if `yaml_file` is not specified during initialization,
    # automatically search for the following configuration file names,
    # the later the file is in the list, the higher its priority
    model_config = SettingsConfigDict(
        yaml_file=["config.yml", "config.yaml"],
        # extra='ignore',
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        assert isinstance(init_settings, InitSettingsSource)
        init_yaml_file = init_settings.init_kwargs.get("yaml_file")
        if init_yaml_file:
            # if the init_settings has a `yaml_file`, use it
            return (YamlConfigSettingsSource(settings_cls, yaml_file=init_yaml_file),)
        else:
            # otherwise, use the default searched configuration file
            return (YamlConfigSettingsSource(settings_cls),)


class Endpoint(BaseModel):
    # 防止前缀为 model_ 的配置有冲突
    model_config = ConfigDict(protected_namespaces=())

    api_type: Optional[str] = None
    api_key: str
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    model_engine_map: Optional[Dict[str, str]] = None


class Settings(YamlBaseSettings):
    host: str = "127.0.0.1"
    """The host address for the FastAPI application."""
    port: int = 8000
    """The port for the FastAPI application."""

    endpoints: List[Endpoint] = Field(..., min_length=1)
    """List of API endpoints configurations."""

    llm_model: str
    """The LLM model to use."""

    db_url: str
    """Database connection URL."""

    meeting_data_root: Path
    """Root directory for meeting data storage."""

    spa_path: Optional[Path] = None
    """Path to the Single Page Application (SPA) static files."""

    funasr_uri: str
    """URI for the FunASR service."""

    save_pcm: bool = False
    """Whether to save PCM audio files. It consumes a lot of disk space."""

    access_token_expire: timedelta = timedelta(days=1)
    """Access token expiration duration."""


settings = Settings()  # type: ignore
