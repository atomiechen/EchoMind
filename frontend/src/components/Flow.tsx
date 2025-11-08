import { useEffect, useCallback, useState, useRef } from "react";
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  // MiniMap,
  Controls,
  Position,
  Background,
  ControlButton,
  type Edge,
  type OnNodeDrag,
  useNodesInitialized,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import '@xyflow/react/dist/base.css';
import { useSocket } from "@/lib/socket";
import type { Issue as IssueData, Position as PositionData } from "@/client/types.gen.js";
import type { CustomNodeType } from "@/lib/definitions";
import { Button, Loader } from "@mantine/core";
import { toPng } from "html-to-image";
import { meetingsManualUpdate } from "@/client/sdk.gen.js";
import { applyDagreLayout, assertIssueNode, assertNotUndefined, moveChildNodes, newNode } from "@/lib/utils";
import { useMeetingStore } from "@/store/meetingStore";
import { useValueChange } from "@/hooks/useValueChange";
import { useTranslation } from "react-i18next";
import { IssuePositionNode } from "./IssuePositionNode";


const nodeDefaults = {
  sourcePosition: Position.Right,
  targetPosition: Position.Left,
  position: { x: 0, y: 0 },
};

const addPositionNode = (nodes: CustomNodeType[], edges: Edge[], positionNode: PositionData, isEditable: boolean) => {
  let new_nodes: CustomNodeType[];
  const new_edges: Edge[] = [...edges];
  // console.log("positionNode", positionNode);
  const positionNodeId = `${positionNode.full_id}`;

  // 找到 parent node
  const parentNodeId = `${positionNode.full_id.split('.')[0]}`;

  if (nodes.find(node => node.id === positionNodeId)) {
    // return { new_nodes, new_edges };
    // 修改观点节点的内容
    new_nodes = nodes.map(node => (
      node.id === positionNodeId ? newNode(node, { 
        data: { content: positionNode.content, confirmed: positionNode.type === "confirmed" ? true : false } 
      }) : node
    ));
  } else {
    // 添加新的 position node
    new_nodes = [...nodes, {
      id: positionNodeId,
      type: 'position',
      dragHandle: '.custom-drag-handle',
      data: {
        isCollapsed: false,
        content: positionNode.content,
        confirmed: positionNode.type === "confirmed" ? true : false,
        editable: isEditable,
        deletable: true,  // position都可删除
      },
      ...nodeDefaults,
    }];

    // 添加新的 edge
    new_edges.push({
      id: `edge-${parentNodeId}-${positionNodeId}`,
      source: parentNodeId,
      target: positionNodeId,
      data: { label: '' },
    });
  }

  return { new_nodes, new_edges };
};

const addIssueNode = (nodes: CustomNodeType[], edges: Edge[], issueNode: IssueData, chosen_id: string, isEditable: boolean) => {
  let new_nodes: CustomNodeType[];
  let new_edges = [...edges];
  // console.log("issueNode", issueNode);
  const issueNodeId = `${issueNode.full_id}`;

  if (nodes.find(node => node.id === issueNodeId)) {
    // return { new_nodes, new_edges };
    // 修改议题节点的内容
    new_nodes = nodes.map(node => {
      if (node.id === issueNodeId) {
        assertIssueNode(node);
        return { ...node, data: { ...node.data, content: issueNode.content, confirmed: issueNode.type === "confirmed" ? true : false, chosen: chosen_id === issueNodeId ? true : false } };
      }
      return node;
    });
  } else {
    // 添加新的 issue node
    new_nodes = [...nodes, {
      id: issueNodeId,
      type: 'issue',
      dragHandle: '.custom-drag-handle',
      data: {
        isCollapsed: false,
        content: issueNode.content,
        chosen: chosen_id === issueNodeId ? true : false,
        confirmed: issueNode.type === "confirmed" ? true : false,
        editable: isEditable,
        deletable: issueNode.source ? true : false,  // 根节点不可删除
      },
      ...nodeDefaults,
    }];

    // 添加新的 edge
    if (issueNode.source) {
      const fromNodeId = `${issueNode.source.target_id}`;
      new_edges.push({
        id: `edge-${fromNodeId}-${issueNodeId}`,
        source: fromNodeId,
        target: issueNodeId,
        label: issueNode.source.content,
        animated: true,
      });
    }
  }
  // 添加新的 position nodes
  issueNode.positions.forEach((positionNode, index) => {
    const { new_nodes: new_position_nodes, new_edges: new_position_edges } = addPositionNode(new_nodes, new_edges, positionNode, isEditable);
    new_nodes = new_position_nodes;
    new_edges = new_position_edges;
  });
  return { new_nodes, new_edges };
};

const initializeElements = (issue_map: IssueData[],  chosen_id: string, isEditable: boolean) => {
  let nodes: CustomNodeType[] = [];
  let edges: Edge[] = [];
  issue_map.forEach((issue, index) => {
    // 调用 addIssueNode
    const { new_nodes, new_edges } = addIssueNode(nodes, edges, issue, chosen_id, isEditable);
    nodes = new_nodes;
    edges = new_edges;
  });
  // 删除新的 issue map 里没有的结点
  const all_ids_in_issue_map: string[] = [];
  issue_map.forEach(issue => {
    all_ids_in_issue_map.push(issue.full_id);
    issue.positions.forEach(position => {
      all_ids_in_issue_map.push(position.full_id);
    });
  });
  nodes = nodes.filter(node => all_ids_in_issue_map.includes(node.id));
  edges = edges.filter(edge => nodes.some(node => node.id === edge.source || node.id === edge.target));
  return { nodes, edges };
};


const nodeTypes = {
  position: IssuePositionNode,
  issue: IssuePositionNode,
};


export default function Flow({ initialNodeData, isEditable }: { initialNodeData: IssueData[], isEditable: boolean }) {
  const { t } = useTranslation();
  const { fitView } = useReactFlow<CustomNodeType>();

  // 根据传入数据提供节点和边的初始值
  console.log("initialNodeData", initialNodeData);
  const initialized = initializeElements(initialNodeData, "-1", isEditable);
  const hasFitView = useRef(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<CustomNodeType>(initialized.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initialized.edges);
  // 监听 initialNodeData 变化，更新 nodes 和 edges
  useValueChange((newInitialNodeData) => {
    const initialized = initializeElements(newInitialNodeData, "-1", isEditable);
    setNodes(initialized.nodes);
    setEdges(initialized.edges);
    hasFitView.current = false; // 重置标志，以便重新 fitView
  }, initialNodeData);
  const { getNodes, getEdges } = useReactFlow<CustomNodeType>();
  const nodesInitialized = useNodesInitialized();
  const flowRef = useRef(null);
  const [draggingNode, setDraggingNode] = useState<CustomNodeType | undefined>(undefined);
  const [running, setRunning] = useState(false);

  const meetingHashId = useMeetingStore(s => s.meetingHashId);

  const onNodeDragStart: OnNodeDrag<CustomNodeType> = (event, node) => {
    setDraggingNode(node);
  };

  const onNodeDragStop: OnNodeDrag<CustomNodeType> = useCallback((event, node) => {
    assertNotUndefined(draggingNode, 'draggingNode is undefined');
    const dx = node.position.x - draggingNode.position.x;
    const dy = node.position.y - draggingNode.position.y;

    // Move the dragging node and its children
    const updatedNodes = nodes.map(n => {
      if (n.id === node.id) {
        return node; // update the position of the dragging node
      }
      return n;
    });

    // Get all updated child nodes recursively
    const allUpdatedNodes = moveChildNodes(nodes, edges, node.id, dx, dy);

    // Combine and deduplicate the nodes
    const finalUpdatedNodes = updatedNodes.map(n => {
      const updatedNode = allUpdatedNodes.find(un => un.id === n.id);
      return updatedNode || n;
    });

    setNodes(finalUpdatedNodes);
    setDraggingNode(undefined);
  }, [edges, nodes, draggingNode, setNodes]);

  useSocket('updateIssue', useCallback((data) => {
    console.log("onInitialdata111", data);
    const { nodes, edges } = initializeElements(data.issue_map,  data.chosen_id, isEditable);
    setNodes(nodes);
    setEdges(edges);
  }, [setEdges, setNodes, isEditable]));

  // 当 nodes 初始化（测量宽高）完成后，进行 dagre 布局
  // FIXME: 这样会导致节点位置跳动，体验不好，后续需要改进
  useEffect(() => {
    if (nodesInitialized) {
      const layouted = applyDagreLayout(getNodes(), getEdges());
      setNodes([...layouted.nodes]);
      setEdges([...layouted.edges]);

      // fit view for initial load
      if (!hasFitView.current) {
        fitView();
        hasFitView.current = true;
      }
    }
  }, [nodesInitialized, getEdges, getNodes, setEdges, setNodes, fitView]);

  useSocket('statusAI', useCallback((data) => {
    console.log("onStatusAI", data);
    setRunning(data.running);
  }, []));

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      ref={flowRef}
      minZoom={0.1}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeDragStart={isEditable ? onNodeDragStart : undefined} // 禁用拖动
      onNodeDragStop={isEditable ? onNodeDragStop : undefined} // 禁用拖动停止
      style={{
        height: '100%',
      }}
      deleteKeyCode={isEditable ? 'Delete' : null} // 禁用删除
      nodeTypes={nodeTypes}
      fitView
      proOptions={{ hideAttribution: true }}
    >
      {/* <MiniMap /> */}
      <Controls>
      <ControlButton onClick={() => {
            if(flowRef.current === null) return
            toPng(flowRef.current, {
                filter: node => !(
                    node?.classList?.contains('react-flow__minimap') ||
                    node?.classList?.contains('react-flow__controls')
                ),
                backgroundColor: 'white',
            }).then(dataUrl => {
                const a = document.createElement('a');
                a.setAttribute('download', 'reactflow.png');
                a.setAttribute('href', dataUrl);
                a.click();
            });
        }}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16px"
              height="16px"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="feather feather-camera"
            >
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
              <circle cx="12" cy="13" r="4"></circle>
            </svg>

        </ControlButton>
      </Controls>
      <div style={{ position: 'absolute', top: '10px', right: '10px' }}>
        {running && <Loader color="blue" size="sm" />}
      </div>
      {isEditable && <Button
        onClick={() => meetingsManualUpdate({ body: { meeting_hash_id: meetingHashId }})}
        variant="light"
        size="xs"
        style={{ margin: '10px', zIndex: 1000 }}
      >
        {t('updateGraph')}
      </Button>}
      <Background />
    </ReactFlow>
  );
};
