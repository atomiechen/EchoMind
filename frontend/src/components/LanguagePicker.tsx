import { IconWorld } from '@tabler/icons-react';
import { ActionIcon, Menu } from '@mantine/core';
import { useTranslation } from 'react-i18next';

const data = [
  { key: 'en', label: 'en / English' },
  { key: 'zh', label: 'zh / 中文' },
];

export function LanguagePicker() {
  const { i18n } = useTranslation();
  const items = data.map((item) => (
    <Menu.Item
      key={item.key}
      onClick={() => i18n.changeLanguage(item.key)}
    >
      {item.label}
    </Menu.Item>
  ));

  return (
    <Menu
      radius="md"
      withinPortal
      position="bottom-end"
      trigger="hover"
    >
      <Menu.Target>
        <ActionIcon size={40} variant="subtle" aria-label="Settings" color='dark.5'>
          <IconWorld size={24} stroke={1.5} />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>{items}</Menu.Dropdown>
    </Menu>
  );
}
