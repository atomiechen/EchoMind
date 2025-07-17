import { useEffect, useState, useRef, useCallback } from "react";
import { Button, Flex, Input, Text, Box, Code, TagsInput, Group, ActionIcon, useMantineTheme, Modal } from '@mantine/core';
import { useParams } from "react-router";
import { IconPencil  } from '@tabler/icons-react';
import { IconChevronRight, IconChevronLeft } from '@tabler/icons-react';
import Flow from "@/components/Flow";
import CardList from "@/components/CardList";
import { Recorder } from "@/components/Recorder";
import { useMeeting } from "@/hooks/useMeeting";
import { message } from "@/lib/notifications";
import { useMediaQuery } from '@mantine/hooks';
import { SummaryPoints } from "@/components/SummaryPoints";
import { useSocket } from "@/lib/socket";
import { meetingsUpdateHotWords } from "@/client";
import { useMeetingStore } from "@/store/meetingStore";
import { useShallow } from "zustand/react/shallow";
import { useSuspenseQuery } from "@tanstack/react-query";
import { meetingsRequestTotalOptions } from "@/client/@tanstack/react-query.gen";
import type { SendAsrData } from "@/lib/models";
import { SideResizable } from "@/components/SideResizable/SideResizable";
import { useValueChange } from "@/hooks/useValueChange";
import { useTranslation } from "react-i18next";


export async function Loader({ params }: { params: { meetingId: string } }) {
  return {
    // header: "liveDiscussion",
    documentTitle: "liveDiscussion",
  }
}


export default function OnlineMeeting() {
    // 请求所有的数据
    const params = useParams();
    const { data: initialAsrData } = useSuspenseQuery(meetingsRequestTotalOptions({ body: { meeting_id: params.meetingId } }))

    const [changeTitle, setChangeTitle] = useState<boolean>(false); // 是否正在修改标题
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

    const scrollAreaRef = useRef<HTMLDivElement>(null);

    // 结束会议和离开会议的模态框
    const [action, setAction] = useState<'end' | 'leave' | null>(null); // 'end' 表示结束会议，'leave' 表示离开会议
    const [isModalOpen, setIsModalOpen] = useState(false);

    const {
        leaveMeeting, endMeeting, changeTitle: execChangeTitle,
    } = useMeeting();

    const [setMeeting, meetingHashId, title, hotWords, isHost, meetingType, setHeaderContent] = useMeetingStore(
        useShallow((s) => [s.setMeeting, s.meetingHashId, s.topic, s.hotwords, s.isHost, s.type, s.setHeaderContent])
    );
    const meetingTypeGraph = (meetingType === 'graph');
    const setTitle = useCallback((title: string) => setMeeting({ topic: title }), [setMeeting]);
    const setHotWords = (hotwords: string[]) => setMeeting({ hotwords });

    useEffect(() => {
        setMeeting({
            topic: initialAsrData.topic, // 设置会议标题
            meetingId: initialAsrData.meeting_id, // 设置会议id
            meetingHashId: initialAsrData.meeting_hash_id, // 设置会议号（hash_id）
            isHost: initialAsrData.role === "host", // 设置是否为主持人
            type: initialAsrData.ai_type, // 设置会议类型
        })
    }, [initialAsrData, setMeeting]);

    // 设置页眉标题，必须用useEffect，否则卡死
    const [tempTitle, setTempTitle] = useState(title);

    useEffect(() => {
        setTempTitle(title);  // 确保 title 更新时，tempTitle 也会同步
        console.log("Updated title:", title); // 监听 title 变化后输出
    }, [title]);

    useEffect(() => {
        setHeaderContent(
            <>
                {t('meetingHashId')}<Code fw={700}>{String(meetingHashId)}</Code>
                {t('role')}<Code fw={700}>{isHost ? t('host') : t('participant')}</Code>

                {t('topic')}
                {changeTitle ?
                    <>
                        <Input defaultValue={tempTitle} onChange={(e) => setTempTitle(e.target.value)} />
                        <Button onClick={() => {
                            console.log("new title:", tempTitle);
                            setTitle(tempTitle);
                            console.log("title:", title);
                            execChangeTitle(tempTitle);
                            setChangeTitle(false);
                        }}>{t('confirm')}</Button>
                        <Button onClick={() => {
                            setTempTitle(title);
                            setChangeTitle(false);
                        }}>{t('cancel')}</Button>
                    </>
                    :
                    <Group gap={0}>
                        <Code fw={700}>{title}</Code>
                        <ActionIcon variant="subtle" style={{ margin: 5 }} onClick={() => setChangeTitle(true)}><IconPencil size={16} /></ActionIcon>
                    </Group>
                }
                 <Group gap={0}>
                    <Button variant="subtle" style={{ margin: 5 }} onClick={() => handleButtonClick('end')}>
                        {t('endMeeting')}
                    </Button>
                    <Button variant="subtle" style={{ margin: 5 }} onClick={() => handleButtonClick('leave')}>
                        {t('leaveMeeting')}
                    </Button>
                </Group>
                
                
            </>
        );
    }, [isHost, meetingHashId, changeTitle, title, tempTitle, execChangeTitle, setHeaderContent, setTitle, t]);

    const handleButtonClick = (actionType: 'end' | 'leave') => {
        setAction(actionType);
        setIsModalOpen(true);
      };
    
      const handleConfirm = () => {
        if (action === 'end') {
          endMeeting(true);
        } else if (action === 'leave') {
          leaveMeeting(true);
        }
        setIsModalOpen(false); // 关闭弹窗
      };

    // // --------- 界面展示功能函数相关 end ---------



    // ---------- socket related begin ----------

    // 正确排序：必须先展示全部转写数据，再展示后来收到的每一小份update
    const handleAsrResult = useCallback((data: SendAsrData) => {
        console.log(data);
        // 显示在列表的最后端
        setOnlineTransData((prevData) => ({
            ...prevData,
            sentences: [...prevData.sentences, ...data.sentences],
            speaker: {
                ...prevData.speaker,
                ...data.speaker,
            },
        }));
        if (scrollAreaRef.current) {
            scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
        }
    }, []);

    useSocket('sendCurrent', handleAsrResult);

    // ---------- socket related end ----------

    return (
        <Flex style={{ height: '100%' }}>
            {/* 侧边栏 */}
            <Modal
                opened={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={action === 'end' ? t('endMeeting') : t('leaveMeeting')}
            >
                <Text>
                {t(action === 'end' ? 'endMeetingConfirm' : 'leaveMeetingConfirm')}
                </Text>
                <Group align="right" mt="md">
                <Button variant="outline" onClick={() => setIsModalOpen(false)}>
                    {t('cancel')}
                </Button>
                <Button color="red" onClick={handleConfirm}>
                    {t(action === 'end' ? 'endMeeting' : 'leaveMeeting')}
                </Button>
                </Group>
            </Modal>
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
                        <Group grow preventGrowOverflow={false} gap='xs' pt='xs'>
                            <TagsInput
                                data={[]}
                                value={hotWords}
                                onChange={setHotWords}
                                // label="热词 Hot words"
                                placeholder={t('hotwordsHelp')}
                                splitChars={[',', '|']}
                                clearable
                                size='xs'
                                style={{ flexGrow: 9 }}
                            />
                            <Button variant="subtle" p={0} size='xs'
                                style={{ flexGrow: 1 }}
                                onClick={() => {
                                    meetingsUpdateHotWords({ body: { meeting_hash_id: meetingHashId, hot_words: hotWords } }).then((res) => {
                                        console.log("update hot words:", res);
                                        message(t('hotwordsSuccess'));
                                    }).catch((error) => {
                                        console.error("Error updating hot words:", error);
                                    });
                                }}
                            >
                                {t('updateHotwords')}
                            </Button>
                        </Group>
                        <CardList trans={onlineTransData} />
                        <Recorder />
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
                    <Flow initialNodeData={initialAsrData.issue_map} isEditable={true} />
                    :
                    <SummaryPoints meeting_hash_id={meetingHashId} topic={title} />
                }
            </Flex>
        </Flex >
    );
}
