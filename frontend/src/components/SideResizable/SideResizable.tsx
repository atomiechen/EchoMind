import { Resizable } from 're-resizable';
import classes from './SideResizable.module.css';


type Side = 'top' | 'right' | 'bottom' | 'left';

interface SideResizableProps extends Omit<React.ComponentProps<typeof Resizable>, 'enable' | 'handleClasses'> {
  side: Side; // 用户传入可拖拽边
  enabled?: boolean; // 是否启用拖拽
}


/**
 * 单边可拖拽的盒子
 */
export function SideResizable({ side, enabled = true, ...rest }: SideResizableProps) {
  // 构建 enable 对象，只开启指定边的拖拽
  const enable = {
    top: false,
    right: false,
    bottom: false,
    left: false,
    topRight: false,
    bottomRight: false,
    bottomLeft: false,
    topLeft: false,
    ...(enabled ? { [side]: true } : {}),
  };

  // 构建 handleClasses 对象，配置拖拽手柄的样式
  const handleClasses = {
    [side]: classes.resizer,
  };

  return (
    <Resizable 
      enable={enable}
      handleClasses={handleClasses}
      {...rest}
    />
  );
}
