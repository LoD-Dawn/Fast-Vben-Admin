import type { VbenFormSchema } from '#/adapter/form';

import { z } from '#/adapter/form';

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        max: 1024,
        min: 1,
      },
      fieldName: 'max_size_mb',
      label: '最大文件大小 MB',
      rules: z.number().min(1, '最大文件大小必须大于 0'),
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 4,
      },
      fieldName: 'allowed_extensions',
      label: '允许扩展名',
      rules: z.string().min(1, '请输入允许扩展名'),
    },
    {
      component: 'Switch',
      fieldName: 'default_public',
      label: '默认公开访问',
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        max: 86_400,
        min: 60,
      },
      fieldName: 'presigned_url_expire_seconds',
      label: '下载链接有效期秒',
      rules: z.number().min(60, '有效期不能小于 60 秒'),
    },
  ];
}
