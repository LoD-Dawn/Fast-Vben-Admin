# 企业 OIDC 配置

## 范围

系统作为企业身份提供方的 OIDC Client，使用授权码流和 PKCE 登录管理端。它只映射已有本地用户，不会根据外部邮箱自动创建账户。

回调完成后，后端仅向前端登录 URL 交付一次性短期票据；前端随后立即清除地址栏并调用票据交换接口获取本系统 JWT。访问令牌不会出现在回调 URL、查询参数或操作日志中。

## 身份提供方要求

- 支持 OpenID Connect Discovery、授权码流和 PKCE S256。
- ID Token 使用 RSA 或 ECDSA 签名，并通过 JWKS 发布签名公钥。
- ID Token 必须包含 `sub`、`iss`、`aud`、`exp`、`iat`、`nonce`、`email`；默认还要求 `email_verified=true`。
- 生产环境的 issuer、discovery、authorization、token 和 JWKS 地址必须使用 HTTPS。

## 环境变量

至少设置以下变量后，登录页才会显示“企业单点登录”入口：

```dotenv
ENTERPRISE_OIDC_ENABLED=true
ENTERPRISE_OIDC_ISSUER=https://id.example.com
ENTERPRISE_OIDC_CLIENT_ID=fast-vben-admin
ENTERPRISE_OIDC_CLIENT_SECRET=replace-with-a-secret
ENTERPRISE_OIDC_REDIRECT_URI=https://api.example.com/api/v1/login/enterprise-oidc/callback
ENTERPRISE_OIDC_FRONTEND_LOGIN_URL=https://admin.example.com/#/auth/login
```

默认 discovery 地址为 `${ENTERPRISE_OIDC_ISSUER}/.well-known/openid-configuration`。非标准地址可使用 `ENTERPRISE_OIDC_DISCOVERY_URL` 覆盖。客户端密钥只保存在部署环境，不会返回到前端。

`ENTERPRISE_OIDC_FRONTEND_LOGIN_URL` 应设置为前端实际登录页。默认回退为 `${FRONTEND_HOST}/auth/login`；生产构建默认使用 Hash 路由时需显式使用 `https://admin.example.com/#/auth/login`。

## 用户、角色和启用状态

- 首次登录按 `email` 查找本地用户，并绑定不可变的外部 `sub`；后续登录优先使用该绑定，避免邮箱变更造成账户串联。
- 找不到本地用户、邮箱未验证或本地用户已禁用时，登录会被拒绝。
- 默认 `ENTERPRISE_OIDC_ROLE_SYNC_MODE=disabled`，保留本地角色。设置为 `replace` 后，系统读取 `ENTERPRISE_OIDC_ROLE_CLAIM`（默认 `groups`），按 `ENTERPRISE_OIDC_ROLE_MAPPING` JSON 同步非超级管理员的全部角色。例如：

```dotenv
ENTERPRISE_OIDC_ROLE_SYNC_MODE=replace
ENTERPRISE_OIDC_ROLE_MAPPING={"idp-admin":"admin","idp-ops":["user","ops"]}
```

映射到的本地角色码必须已存在；未知角色会拒绝登录，避免错误配置扩大权限。

- 默认不改变本地启用状态。设置 `ENTERPRISE_OIDC_SYNC_ACTIVE_STATUS=true` 后，外部 `active` claim 为 `false` 会禁用本地账户并撤销现有会话；为 `true` 时可重新启用。

## 安全与验证

- 授权 state、PKCE verifier、nonce 和一次性交接票据均只短期保存于数据库，并在使用后立即失效。
- ID Token 会校验签名、JWKS key id、允许的非对称算法、issuer、audience、有效期和 nonce。
- 登录成功与失败写入登录日志；票据交换路径不写操作日志正文。
- 后端测试使用模拟身份源覆盖 PKCE、nonce、签名验证、本地用户绑定、角色同步、启用状态同步和票据重放。实际企业身份提供方联调应在单独的测试环境执行。
