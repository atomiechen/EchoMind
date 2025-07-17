import { useMeeting } from "@/hooks/useMeeting";
import { useSocket } from "@/lib/socket";
import { useMeetingStore } from "@/store/meetingStore";
import { useCallback, useEffect } from "react";
import { Outlet, useLocation } from "react-router";


export default function AppLayout() {
  const setMeeting = useMeetingStore((state) => state.setMeeting);
  const hasMeeting = useMeetingStore((state) => state.hasMeeting);
  const { leaveMeeting } = useMeeting();
  const location = useLocation();

  useEffect(() => {
    // check if pathname startswith /onlinetest/
    if (!location.pathname.match(/^\/online\//) && !location.pathname.match(/^\/record\//)) {
      console.log('leave meeting on route change', location.pathname);
      leaveMeeting();
    }
  }, [location, hasMeeting, leaveMeeting]);

  useSocket("identification", useCallback((data) => {
    console.log("Received identification event", data);
    setMeeting({ isHost: data.role === 'host' });
  }, [setMeeting]));
  return <Outlet />;
}
