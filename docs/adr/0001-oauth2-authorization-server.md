# ADR-0001: OAuth2 授权服务器角色与首期范围

状态：已接受

日期：2026-07-14

## 背景

项目已经有 OAuth2 客户端与令牌管理数据模型，但没有授权端点、令牌端点、PKCE 校验或撤销协议，不能宣称具备 OAuth2/SSO 能力。现有模型以“本系统管理第三方应用客户端”为中心，最适合首先承担 Authorization Server 角色。

## 决策

本系统首期作为 OAuth2 Authorization Server 实现，协议边界如下：

- 授权模式只支持 `authorization_code`（必须 PKCE S256）和 `refresh_token`。
- 首期客户端类型为 public client 与 confidential client；public client 不保存 client secret，confidential client 使用加密保存的 secret。
- 授权端点必须要求已登录、已启用的本地用户，并在同意页确认应用、回调地址与 scope。
- 授权码单次使用、短生命周期，并绑定 client、redirect URI、用户、scope 与 PKCE challenge。
- 访问令牌、刷新令牌、授权码仅保存不可逆哈希；管理端不得展示原始值。
- 刷新令牌轮换，重放时撤销令牌链。
- 撤销端点与客户端禁用必须立即使有效令牌失效。
- OIDC、`id_token`、动态客户端注册、`client_credentials`、资源服务器和外部身份提供商接入不进入首期范围。

## 原因

- 与现有 OAuth2 客户端管理和权限模型一致，避免同时承担客户端与授权服务器两个角色造成的配置和安全复杂度。
- Authorization Code + PKCE 是浏览器、桌面和移动应用的当前安全基线，隐式和密码授权模式不应新增。
- 先完成可验证的本地授权协议，再增加企业 IdP 或社交登录适配器，便于隔离故障和安全审计。

## 后果

- 现有 OAuth2 客户端/令牌管理页需迁移到新的哈希令牌模型，现有明文字段不得用于新签发令牌。
- 需要增加授权码、令牌族、用户同意记录及相关 Alembic 迁移。
- 需要采用 Authlib 或同等级成熟库完成协议解析和错误响应，不手写 OAuth2 协议细节。
- 真实第三方登录被拆为独立的 OAuth2 Client/provider adapter 工作，需要平台账号、回调域名和密钥后才能验收。

## 验收条件

- 覆盖 redirect URI 不匹配、缺少或错误 PKCE、重复授权码、过期授权码、刷新令牌重放、撤销后访问等协议测试。
- 管理端、日志、错误响应和数据库中均不泄露 client secret、授权码、访问令牌、刷新令牌或用户密码。
- 至少一个测试客户端完成本地授权码登录、刷新和撤销闭环。
