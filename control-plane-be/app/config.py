from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (plain postgresql:// — used by Prisma; no driver suffix needed)
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/controlplane"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    SECRET_KEY: str = "change-this-to-a-long-random-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Object storage (S3 / MinIO)
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_ENDPOINT_URL: str = "http://minio:9000"
    # Public URL for presigned links sent to the browser.
    # Set this to the externally reachable MinIO address, e.g. http://localhost:9000
    # Defaults to AWS_ENDPOINT_URL when not set (works if MinIO is directly public).
    AWS_PUBLIC_ENDPOINT_URL: str = ""
    AWS_BUCKET_NAME: str = "controlplane"
    AWS_REGION: str = "us-east-1"

    # Slack (for notifications)
    SLACK_BOT_TOKEN: str = ""
    SLACK_SUPPORT_CHANNEL: str = "#control-plane-support"
    SLACK_METRICS_CHANNEL: str = ""

    # Prometheus (internal service URL for server-side queries)
    PROMETHEUS_URL: str = "http://prometheus:9090"

    # Metrics EOD report — hour (0-23) in UTC to send the daily Slack report
    METRICS_REPORT_HOUR: int = 23

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 50

    # Maintenance module
    MAINTENANCE_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/maintenance_db"
    MAINTENANCE_JWT_SECRET: str = "change-this-maintenance-secret-in-production"
    MAINTENANCE_ADMIN_EMAIL: str = "maintenance_admin@haval.com"
    MAINTENANCE_ADMIN_PASSWORD: str = "ChangeMe123!"
    MAINTENANCE_ADMIN_NAME: str = "Maintenance Admin"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
