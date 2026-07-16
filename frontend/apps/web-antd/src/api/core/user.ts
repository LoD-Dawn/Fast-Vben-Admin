import type { UserInfo } from '@vben/types';

import { getCurrentUserApi } from './auth';

export const DEFAULT_AVATAR = '/images/avatar-v1.webp';

export function mapCurrentUserToUserInfo(
  user: Awaited<ReturnType<typeof getCurrentUserApi>>,
) {
  const role = user.is_superuser ? 'super' : 'user';

  return {
    avatar: user.avatar_url || DEFAULT_AVATAR,
    desc: user.is_superuser ? 'Super administrator' : 'User',
    homePath: '/dashboard',
    realName: user.full_name || user.email,
    roles: [role],
    token: '',
    userId: user.id,
    username: user.email,
  } satisfies UserInfo;
}

/**
 * 获取用户信息
 */
export async function getUserInfoApi() {
  return mapCurrentUserToUserInfo(await getCurrentUserApi());
}
