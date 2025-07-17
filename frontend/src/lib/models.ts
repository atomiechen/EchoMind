/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AllSummaries {
  summaries: SummaryData[];
}
export interface SummaryData {
  id: number;
  summary: string;
}
export interface AudioChunk {
  meeting_id: string;
  file_id: number | null;
  begin: number;
  end: number;
  base64: string;
  encodingType: string;
}
export interface AudioChunkMeta {
  meeting_id: string;
  encodingType: string;
  begin: number;
  end: number;
}
export interface Identification {
  role: "host" | "participant";
}
export interface Issue {
  full_id: string;
  content: string;
  type?: "confirmed" | "deleted" | "unconfirmed";
  issue_id: number;
  positions: Position[];
  source?: Relation | null;
}
export interface Position {
  full_id: string;
  content: string;
  type?: "confirmed" | "deleted" | "unconfirmed";
  position_id: number;
  ref?: string | null;
  pros: Argument[];
  cons: Argument[];
  note?: string | null;
  generated_issue?: boolean;
  [k: string]: unknown;
}
export interface Argument {
  full_id: string;
  content: string;
  type?: "confirmed" | "deleted" | "unconfirmed";
  argument_id: string;
  ref?: string | null;
  [k: string]: unknown;
}
export interface Relation {
  target_id: string;
  target_type: string;
  target_content: string;
  content: string;
  [k: string]: unknown;
}
export interface ProcessStatus {
  running: boolean;
}
export interface RequestData {
  cnt: number;
}
export interface SendAsrData {
  speaker: {
    [k: string]: string;
  };
  sentences: AsrSentence[];
}
export interface AsrSentence {
  content: string;
  time_range: number[];
  speaker_id: string;
  [k: string]: unknown;
}
export interface ToggleMicrophone {
  meeting_id: string;
  enable: boolean;
  timestamp: number;
}
export interface UpdateIssueData {
  issue_map: Issue[];
  chosen_id: string;
}
