import { Link, useLocation } from 'react-router';
import { useEffect, useRef } from 'react';
import classes from './Navbar.module.css';

import type { NavItem } from '@/lib/definitions';

interface NavbarProps {
  data: NavItem[];
  clickHandler: (label: string) => void;
  selectedItem?: string | null;
}

export function Navbar({ data, clickHandler, selectedItem }: NavbarProps) {
  const location = useLocation();

  /**
   * itemRefs 用于存放每个 Link 对应的 DOM 元素
   * key: NavItem.label, value: HTMLAnchorElement
   */
  const itemRefs = useRef<{ [key: string]: HTMLAnchorElement | null }>({});

  // 当 selectedItem 改变时，让对应 Link 滚动到可视区域的中央
  useEffect(() => {
    if (selectedItem && itemRefs.current[selectedItem]) {
      itemRefs.current[selectedItem].scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'nearest',
      });
    }
  }, [selectedItem]);

  const links = data.map((item) => (
    <Link
      ref={(el) => {
        // 将当前 Link 的元素存到 itemRefs 里
        itemRefs.current[item.label] = el;
      }}
      className={classes.link}
      data-active={location.pathname === encodeURI(item.link) || undefined}
      to={item.link}
      key={item.link}
      onClick={() => {
        clickHandler(item.label);
      }}
      style={selectedItem ? {
        backgroundColor: selectedItem === item.label ? '#F5F5F5' : 'white', // 选中时背景变为浅灰色
        color: 'black',
        fontWeight: selectedItem === item.label ? 'bold' : 'normal',        // 选中时字体加粗
      } : undefined}
    >
      <item.icon className={classes.linkIcon} stroke={1.5} />
      <span>{item.label}</span>
    </Link>
  ));

  return (
    <nav className={classes.navbar}>
      <div className={classes.navbarMain}>
        {links}
      </div>
    </nav>
  );
}
