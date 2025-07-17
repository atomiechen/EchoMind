import type { Node } from '@xyflow/react';
import React from 'react';


export interface NavItem {
	link: string,
	label: string,
	icon: React.ElementType,
}


export type CustomNodeData = {
	isCollapsed: boolean;
	content: string;
	confirmed: boolean;
	editable: boolean;
	deletable: boolean;
}

type IssueNodeData = CustomNodeData & {
	chosen: boolean;
}

type PositionNodeData = CustomNodeData;

export type IssueNode = Node<IssueNodeData, 'issue'>;
export type PositionNode = Node<PositionNodeData, 'position'>;

export type CustomNodeType = IssueNode | PositionNode;
