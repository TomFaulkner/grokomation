from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: SettingsConfigDict = SettingsConfigDict(  # type: ignore[incompabileVariableOverride]
        env_file=".env", env_file_encoding="utf-8", secrets_dir="/run/secrets"
    )

    get_prod_hash_command: str = "./get_prod_hash.sh"
    project_path: str
    debug_env: str = ".env.debug.template"
    worktree_base: str = "/tmp/debug-worktrees"


settings = Settings()  # pyright: ignore[reportCallIssue]
