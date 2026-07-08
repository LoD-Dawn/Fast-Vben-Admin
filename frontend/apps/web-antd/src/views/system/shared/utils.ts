import { Modal } from 'ant-design-vue';

export function confirmAction(content: string, title: string) {
  return new Promise<void>((resolve, reject) => {
    Modal.confirm({
      content,
      onCancel() {
        reject(new Error('cancelled'));
      },
      onOk() {
        resolve();
      },
      title,
    });
  });
}

export function buildKeyword(...values: Array<string | undefined>) {
  return values.find((value) => value?.trim())?.trim();
}

export function buildDepartmentTree<
  T extends { id: string; parent_id?: null | string; sort?: number },
>(items: T[]): Array<T & { children: ReturnType<typeof buildDepartmentTree<T>> }> {
  const childrenMap = new Map<null | string, T[]>();
  for (const item of items) {
    const parentId = item.parent_id ?? null;
    const children = childrenMap.get(parentId) ?? [];
    children.push(item);
    childrenMap.set(parentId, children);
  }

  function build(parentId: null | string): Array<T & { children: ReturnType<typeof buildDepartmentTree<T>> }> {
    return (childrenMap.get(parentId) ?? [])
      .sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0))
      .map((item) => ({
        ...item,
        children: build(item.id),
      }));
  }

  return build(null);
}
