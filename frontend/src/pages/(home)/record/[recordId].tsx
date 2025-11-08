import { useEffect, useRef, useState } from "react";
import { Button, Flex, Box, Code, Group, useMantineTheme } from '@mantine/core';
import { useParams } from "react-router";
import { IconChevronRight, IconChevronLeft } from '@tabler/icons-react';
import Flow from "@/components/Flow";
import CardList from "@/components/CardList";
import { useMediaQuery } from '@mantine/hooks';
import { SummaryPoints } from "@/components/SummaryPoints";
import { useMeetingStore } from "@/store/meetingStore";
import { useShallow } from "zustand/react/shallow";
import { useSuspenseQuery } from "@tanstack/react-query";
import { meetingsRequestRecordOptions } from "@/client/@tanstack/react-query.gen";
import type { SendAsrData } from "@/lib/models";
import { SideResizable } from "@/components/SideResizable/SideResizable";
import { useValueChange } from "@/hooks/useValueChange";
import { useTranslation } from "react-i18next";
import { Player, type PlayerHandle } from "@/components/Player";


export async function Loader({ params }: { params: { meetingId: string } }) {
  return {
    // header: "liveDiscussion",
    documentTitle: "discussionDetail",
  }
}


export default function MeetingRecord() {
    // 请求所有的数据
    const params = useParams();
    const { data: initialAsrData } = useSuspenseQuery(meetingsRequestRecordOptions({ body: { meeting_id: params.recordId } }))

    const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);//左侧边栏缩放
    // 渲染从Loader获取的初始转写数据
    const [onlineTransData, setOnlineTransData] = useState<SendAsrData>(initialAsrData);  //实时转写数据
    // 监听 initialAsrData 变化，同步 onlineTransData
    useValueChange((newInitialAsrData) => {
        setOnlineTransData(newInitialAsrData);
    }, initialAsrData);

    const theme = useMantineTheme();
    const isMobile = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`);

    const { t } = useTranslation();

    const [setMeeting, meetingHashId, title, isHost, meetingType, setHeaderContent] = useMeetingStore(
        useShallow((s) => [s.setMeeting, s.meetingHashId, s.topic, s.isHost, s.type, s.setHeaderContent])
    );
    const meetingTypeGraph = (meetingType === 'graph');

    const playerRef = useRef<PlayerHandle>(null);  // 引用 Player 组件实例
    const setCurrentTime = (time: number) => {
      if (playerRef.current) {
        playerRef.current.setCurrentTime(time);
      }
    };

    useEffect(() => {
        setMeeting({
            topic: initialAsrData.topic, // 设置会议标题
            meetingId: initialAsrData.meeting_id, // 设置会议id
            meetingHashId: initialAsrData.meeting_hash_id, // 设置会议号（hash_id）
            isHost: initialAsrData.role === "host", // 设置是否为主持人
            type: initialAsrData.ai_type, // 设置会议类型
        })
    }, [initialAsrData, setMeeting]);

    useEffect(() => {
        setHeaderContent(
            <>
                {t('meetingHashId')}<Code fw={700}>{String(meetingHashId)}</Code>
                {t('role')}<Code fw={700}>{isHost ? t('host') : t('participant')}</Code>
                {t('topic')}
                <Group gap={0}>
                    <Code fw={700}>{title}</Code>
                </Group>
            </>
        );
    }, [isHost, meetingHashId, title, setHeaderContent, t]);

    // // --------- 界面展示功能函数相关 end ---------

    return (
        <Flex style={{ height: '100%' }}>
            {/* 侧边栏 */}
            <Box
                style={(theme) => ({
                    overflow: 'hidden',
                    backgroundColor: '#ffffff',
                    display: 'flex',
                    flexDirection: 'row',
                    position: 'relative',
                    width: leftSidebarCollapsed ? '1.5%' : '45%',
                    padding: 0,
                })}
                renderRoot={isMobile ? undefined : (props) => (
                    <SideResizable
                        defaultSize={{
                            height: '100%',
                            width: '350px',
                        }}
                        minWidth={leftSidebarCollapsed ? '1.5%' : '20%'}
                        maxWidth={leftSidebarCollapsed ? '1.5%' : '100%'}
                        side='right'
                        enabled={!leftSidebarCollapsed}
                        {...props}
                    />
                )}
            >

                {
                    <Flex direction='column'
                        style={
                            leftSidebarCollapsed ?
                                {
                                    display: 'none'
                                }
                                :
                                {
                                    width: "100%",
                                    marginRight: 0,
                                    padding: 0
                                }
                        }>
                        <CardList trans={onlineTransData} setCurrentTime={setCurrentTime} />
                        <Player ref={playerRef} />
                    </Flex>
                }

                <Flex
                    style={{
                        width: leftSidebarCollapsed ? '100%' : 20,
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRight: '1px solid #e0e0e0',
                        backgroundColor: '#ffffff',
                    }}
                >
                    {!isMobile && (
                        <Button
                            onClick={() => setLeftSidebarCollapsed(!leftSidebarCollapsed)}
                            variant="subtle"
                            size="xs"
                            style={{
                                position: 'absolute',
                                right: '-1px',
                                height: '100%',
                                width: leftSidebarCollapsed ? '100%' : 20,
                                padding: 0,
                            }}
                        >
                            {leftSidebarCollapsed ? (
                                <IconChevronRight size={25} width={20} />
                            ) : (
                                <IconChevronLeft size={25} width={20} />
                            )}
                        </Button>
                    )}

                </Flex>
            </Box>
            {/* 右侧 */}

            {/* 导图/文档 */}
            <Flex direction='column' style={{ width: "100%" }}>
                {
                    meetingTypeGraph ?
                    <Flow initialNodeData={initialAsrData.issue_map} isEditable={false} />
                    :
                    <SummaryPoints meeting_hash_id={meetingHashId} topic={title} />
                }
            </Flex>
        </Flex >
    );
}
