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

后端会对默认 `changethis` 值发出安全警告。生产环境建议使用独立 PostgreSQL、HTTPS 反向代理和可靠的文件存储目录。

## 数据库迁移

```bash
cd backend
uv run alembic upgrade head
```

## 文件存储

当前默认使用本地存储，文件元数据保存在 `fileasset` 表中。Compose 已将后端 `/app/backend/uploads` 挂载到 `app-uploads` volume，重启容器后文件不会丢失。生产环境需要定期备份上传目录，并按业务场景限制可上传类型和大小。
