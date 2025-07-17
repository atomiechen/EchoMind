import type { Edge } from "@xyflow/react";
import type { CustomNodeType, IssueNode, PositionNode } from "./definitions";
import dagre from "dagre";

export function assertNotUndefined<T>(
  value: T,
  message = 'Value is undefined',
): asserts value is Exclude<T, undefined> {
  if (value === undefined) {
    throw new Error(message);
  }
}

export function assertIssueNode(node: CustomNodeType): asserts node is IssueNode {
  if (node.type !== 'issue') {
    throw new Error('Node is not an IssueNode');
  }
}

export function assertPositionNode(node: CustomNodeType): asserts node is PositionNode {
  if (node.type !== 'position') {
    throw new Error('Node is not a PositionNode');
  }
}

export function newNode<T extends CustomNodeType>(
  node: T,
  partial: Partial<Omit<T, 'data'>> & { data?: Partial<T['data']> }
): T {
  return {
    ...node,
    ...partial,
    data: { ...node.data, ...partial.data },
  };
}

/**
 * 找到某个节点的所有子孙节点 (不包括自己)
 */
export const getChildren = (id: string, nodes: CustomNodeType[], edges: Edge[]) => {
  console.log("getChildren", id);
  console.log("nodes", nodes);
  const childrenIds: string[] = [];
  const stack = [id];
  while (stack.length > 0) {
    const currentId = stack.pop();
    const children = nodes.filter(node => edges.some(edge => edge.source === currentId && edge.target === node.id));
    console.log("children", children);
    children.forEach(child => {
      stack.push(child.id);
      childrenIds.push(child.id);
    });
  }
  return childrenIds;
};

/**
 * Use dagre for layout
 */
export const applyDagreLayout = (nodes: CustomNodeType[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({ rankdir: 'LR' }); // 从左到右的布局

  edges.forEach(edge => dagreGraph.setEdge(edge.source, edge.target));
  nodes.forEach(node => 
    dagreGraph.setNode(node.id, {
      ...node,
      width: node.measured?.width ?? 0, 
      height: node.measured?.height ?? 0,
    })
  );

  dagre.layout(dagreGraph);

  return {
    nodes: nodes.map((node) => {
      const position = dagreGraph.node(node.id);
      // We are shifting the dagre node position (anchor=center center) to the top left
      // so it matches the React Flow node anchor point (top left).
      const x = position.x - (node.measured?.width ?? 0) / 2;
      const y = position.y - (node.measured?.height ?? 0) / 2;
 
      return { ...node, position: { x, y } };
    }),
    edges,
  };
};

/**
 * 递归移动子节点 Recursively move child nodes
 */
export const moveChildNodes = (nodes: CustomNodeType[], edges: Edge[], parentNodeId: string, deltaX: number, deltaY: number) => {
  // Find all child nodes
  const childNodes = nodes.filter(n => edges.some(e => e.source === parentNodeId && e.target === n.id));

  // Initialize updatedNodes with child nodes
  let updatedNodes: CustomNodeType[] = [];

  childNodes.forEach(child => {
    // Update position of the child node
    const updatedChild = {
      ...child,
      position: {
        x: child.position.x + deltaX,
        y: child.position.y + deltaY,
      },
    };

    // Recursively move child nodes of the child node
    const childUpdatedNodes = moveChildNodes(nodes, edges, child.id, deltaX, deltaY);

    // Add the updated child node and its updated descendants to updatedNodes
    updatedNodes = [...updatedNodes, updatedChild, ...childUpdatedNodes];
  });

  return updatedNodes;
};

// 时间格式化
export const formatDateTime = (dateTime: string) => {
  const date = new Date(dateTime);
  const formattedDate = date.toLocaleDateString(); // 获取年月日
  const formattedTime = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit',second: '2-digit'}); // 获取时分
  return { formattedDate, formattedTime };
};


export const formatedDateTimeString = (dateTime: string) => {
  const { formattedDate, formattedTime } = formatDateTime(dateTime);
  return `${formattedDate} ${formattedTime}`;
}
