import { meetingsJoinMeeting, meetingsLeaveMeeting, meetingsStartMeeting, meetingsEndMeeting, type BodyMeetingsJoinMeeting, type MeetingStart, meetingsChangeTitle } from "@/client";
import { error, showLoading, success, updateError, updateSuccess } from "@/lib/notifications";
import { useNavigate } from "react-router";
import { useMeetingStore } from "@/store/meetingStore";
import { useShallow } from 'zustand/react/shallow'
import { useTranslation } from "react-i18next";
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { invalidateQueryId } from "@/lib/query";

export function useMeeting() {
  const [setMeeting, clearMeeting, hasMeeting] = useMeetingStore(
    useShallow((s) => [s.setMeeting, s.clearMeeting, s.hasMeeting]),
  );
  const navigate = useNavigate();
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  return {
    startMeeting: useCallback((data: MeetingStart) => {
      const id = showLoading(t('startDiscussionLoading'));
      meetingsStartMeeting({
        body: data
      })
      .then((res) => {
        const responseData = res.data;
        console.log("Meeting started successfully:", res);
        updateSuccess(id, t('startDiscussionSuccess'), t('redirecting'));
        setMeeting({
          meetingId: responseData.meeting_id,
          meetingHashId: responseData.meeting_hash_id,
          isHost: true,
          topic: data.topic,
          hotwords: data.hotwords || [],
          type: data.type,
        })
        navigate(`/online/${responseData.meeting_id}`);
      })
      .catch((error) => {
        console.error("Failed to start discussion:", error);
        updateError(id, t('startDiscussionError'), error.detail);
      });
    }, [setMeeting, navigate, t]),

    joinMeeting: useCallback((data: BodyMeetingsJoinMeeting) => {
      const id = showLoading(t('joinDiscussionLoading'));
      meetingsJoinMeeting({
        body: data
      })
      .then((res) => {
        const responseData = res.data;
        if (responseData.code === 0) {
          console.log("Joined discussion successfully:", res);
          updateSuccess(id, t('joinDiscussionSuccess'), t('redirecting'));
          setMeeting({
            meetingId: responseData.meeting_id,
            meetingHashId: responseData.meeting_hash_id,
            isHost: false,
            topic: responseData.topic,
            hotwords: [],
            type: 'graph', // Default type, can be adjusted based on your logic
          });
          navigate(`/online/${responseData.meeting_id}`);
        }
      })
      .catch((error) => {
        console.error("Failed to join discussion:", error);
        updateError(id, t('joinDiscussionError'), error.detail);
      });
    }, [setMeeting, navigate, t]),

    leaveMeeting: useCallback((redirect: boolean = false) => {
      if (hasMeeting()) {
        meetingsLeaveMeeting({
          body: { meeting_id: useMeetingStore.getState().meetingId }
        })
        .then((res) => {
          const responseData = res.data;
          if (responseData.code === 0) {
            console.log("Left discussion successfully:", res);
            success(t('leaveMeetingSuccess'));
            clearMeeting();
            // cache of meetings list may be stale after leaving a meeting
            invalidateQueryId(queryClient, 'meetingsGetAllMeetings');
            invalidateQueryId(queryClient, 'meetingsGetOngoingMeetings');
            if (redirect) {
              navigate('/');
            }
          } else if (responseData.code === 1) {
            error(t('leaveMeetingError'));
          }
        }).catch((error) => {
          console.error("Failed to leave discussion:", error);
          error(t('leaveMeetingError'), error.detail);
        });
      }
    }, [hasMeeting, clearMeeting, navigate, t, queryClient]),

    endMeeting: useCallback((redirect: boolean = false) => {
      if (hasMeeting()) {
        meetingsEndMeeting({
          body: { meeting_id: useMeetingStore.getState().meetingId }
        })
        .then((res) => {
          const responseData = res.data;
          if (responseData.code === 0) {
            console.log("Meeting stopped successfully:", res);
            success(t('endMeetingSuccess'));
            clearMeeting();
            // cache of meetings list may be stale after leaving a meeting
            invalidateQueryId(queryClient, 'meetingsGetAllMeetings');
            invalidateQueryId(queryClient, 'meetingsGetOngoingMeetings');
            if (redirect) {
              navigate('/meeting/history');
            }
          } else if (responseData.code === 1) {
            error(t('endMeetingError'));
          } else if (responseData.code === 2) {
            error(t('endMeetingError'), t('noPermission'));
          }
        }).catch((error) => {
          console.error("Failed to stop discussion:", error);
          error(t('endMeetingError'), error.detail);
        });
      }
    }, [hasMeeting, clearMeeting, navigate, t, queryClient]),

    changeTitle: useCallback((title: string) => {
      meetingsChangeTitle({ body: { title, meeting_id: useMeetingStore.getState().meetingId } })
      .then((res) => {
        const responseData = res.data;
        if (responseData.code === 0) {
            success(t('changeTitleSuccess'));
        } else {
            error(t('changeTitleError'), t('noPermission'));
        }
      }).catch((err) => {
        console.error("Failed to change title:", err);
        error(t('changeTitleError'), err.detail);
      });
    }, [t]),
  };
}
