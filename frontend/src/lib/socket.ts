import { io, Socket } from 'socket.io-client';
import { API_BASE_URL } from '@/lib/constants';
import type { AllSummaries, AudioChunkMeta, Identification, ProcessStatus, RequestData, SendAsrData, ToggleMicrophone, UpdateIssueData } from '@/lib/models';
import { useEffect } from 'react';
import type { ReservedOrUserEventNames, ReservedOrUserListener } from '@socket.io/component-emitter';


// ref: https://socket.io/docs/v4/typescript/
interface ListenEvents {
  noArg: () => void;
  withAck: (d: string, callback: (e: number) => void) => void;
  identification: (d: Identification) => void;
  meetingEnd: () => void;
  requestData: (d: RequestData) => void;
  sendCurrent: (d: SendAsrData) => void;
  updateIssue: (d: UpdateIssueData) => void;
  statusAI: (d: ProcessStatus) => void;
  sendSummaryNew: (d: AllSummaries) => void;
}


interface EmitEvents {
  audioChunk: (d: Int16Array, meta: AudioChunkMeta) => void;
  toggleMic: (data: ToggleMicrophone) => void;
}


// NOTE: 浏览器刷新时，后端需要等一段时间才知道socket断开，所以此时后端会有多个sid对应同一个userid
export const socket: Socket<ListenEvents, EmitEvents> = io(API_BASE_URL, {
    autoConnect: false,  // MUST disable auto connect, otherwise it will connect immediately
    withCredentials: true,
    // ref: https://stackoverflow.com/a/41953165
    // transports: ['websocket'],
    // upgrade: false,
});


// interface SocketReservedEvents {
//     connect: Parameters<typeof socket.on<'connect'>>[1];
//     connect_error: Parameters<typeof socket.on<'connect_error'>>[1];
//     disconnect: Parameters<typeof socket.on<'disconnect'>>[1];
// }


// HACK: get reserved events from socket instance to make `useSocket` have same types as socket.on/off
type AllEventNames = Parameters<typeof socket.on>[0];

type ReservedEventNames = Exclude<AllEventNames, keyof ListenEvents>;

type SocketReservedEvents = {
  [E in ReservedEventNames]: Parameters<typeof socket.on<E>>[1];
};

export function useSocket<Ev extends ReservedOrUserEventNames<SocketReservedEvents, ListenEvents>>(
  ev: Ev,
  listener: ReservedOrUserListener<SocketReservedEvents, ListenEvents, Ev>
) {
  useEffect(() => {
    socket.on(ev, listener as never);

    return () => {
      socket.off(ev, listener as never);
    };
  }, [ev, listener]);
}
