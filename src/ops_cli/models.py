from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Environment = Literal["dev", "staging", "prod"]


class BackupConfig(BaseModel):
    # O Pydantic converte strings recebidas da CLI para Path e valida os tipos.
    source: Path
    destination: Path
    compress: bool = True

    @field_validator("source")
    @classmethod
    def source_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"source does not exist: {value}")
        return value


class DeployConfig(BaseModel):
    artifact: Path
    environment: Environment = "dev"
    # Field permite regras extras; aqui a versao precisa seguir o formato 1.2.3.
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")

    @field_validator("artifact")
    @classmethod
    def artifact_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"artifact does not exist: {value}")
        return value


class CleanConfig(BaseModel):
    target: Path
    # ge=1 significa "greater or equal": no minimo 1 dia.
    older_than_days: int = Field(default=7, ge=1)
    dry_run: bool = False

    @field_validator("target")
    @classmethod
    def target_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"target does not exist: {value}")
        return value


class GenerateConfig(BaseModel):
    # O nome precisa comecar com letra para virar um arquivo/config previsivel.
    name: str = Field(min_length=2, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    environment: Environment = "dev"
    output: Path = Path("generated")
