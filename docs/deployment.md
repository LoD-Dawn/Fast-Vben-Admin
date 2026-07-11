# 部署

## Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

本地执行该命令需要先安装 Docker CLI / Docker Desktop。没有 Docker 的环境只能验证后端、前端和 E2E，Compose 启动需在 CI 或具备 Docker 的机器上补验。

服务默认端口：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/api/v1/openapi.json`
- Adminer：`http://localhost:8080`

## 生产环境变量

生产部署前必须修改：

- `SECRET_KEY`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`
- `DOMAIN`
- `BACKEND_CORS_ORIGINS`
- `UPLOAD_DIR`
- `UPLOAD_MAX_SIZE_MB`
- `UPLOAD_ALLOWED_EXTENSIONS`
- `STORAGE_PROVIDER`
- 当 `STORAGE_PROVIDER=s3` 时的 `S3_BUCKET`、访问密钥和端点

后端会对默认 `changethis` 值发出安全警告。生产环境建议使用独立 PostgreSQL、HTTPS 反向代理和可靠的文件存储目录。

## 数据库迁移

```bash
cd backend
uv run alembic upgrade head
```

## 文件存储

默认使用本地存储，文件元数据保存在 `fileasset` 表中。Compose 已将后端 `/app/backend/uploads` 挂载到 `app-uploads` volume，重启容器后文件不会丢失。

要使用 MinIO 或其他 S3 兼容服务：

1. 设置 `STORAGE_PROVIDER=s3`，并填写 `S3_ENDPOINT_URL`、`S3_BUCKET`、`S3_ACCESS_KEY_ID`、`S3_SECRET_ACCESS_KEY`。
2. MinIO 开发环境可用 `docker compose --profile storage up --build` 启动，API 为 `http://localhost:9000`，控制台为 `http://localhost:9001`。
3. 本地开发可设置 `S3_ADDRESSING_STYLE=path` 和 `S3_AUTO_CREATE_BUCKET=true`；生产环境建议预先创建 bucket 并关闭自动创建。

应用下载接口始终执行文件权限校验；S3 文件还可以从 `GET /api/v1/files/{file_id}/download-url` 获取默认 300 秒有效的预签名 URL，可用 `S3_PRESIGNED_URL_EXPIRE_SECONDS` 调整。
